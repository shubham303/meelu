import { GetObjectCommand, ListObjectsV2Command, S3Client } from "@aws-sdk/client-s3";

const { R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET } = process.env;
if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY || !R2_BUCKET) {
  console.error("Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET.");
  process.exit(1);
}

const LISTS = ["downloads", "waitlist"];
const list = process.argv[2];
if (!LISTS.includes(list)) {
  console.error(`Usage: node --env-file=.env.local scripts/emails-export.mjs <${LISTS.join("|")}> > out.csv`);
  process.exit(1);
}

const s3 = new S3Client({
  region: "auto",
  endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId: R2_ACCESS_KEY_ID, secretAccessKey: R2_SECRET_ACCESS_KEY },
});

const keys = [];
let token;
do {
  const page = await s3.send(
    new ListObjectsV2Command({ Bucket: R2_BUCKET, Prefix: `${list}/`, ContinuationToken: token }),
  );
  for (const object of page.Contents ?? []) keys.push(object.Key);
  token = page.IsTruncated ? page.NextContinuationToken : undefined;
} while (token);

const entries = [];
for (const key of keys) {
  const object = await s3.send(new GetObjectCommand({ Bucket: R2_BUCKET, Key: key }));
  entries.push(JSON.parse(await object.Body.transformToString()));
}

entries.sort((a, b) => a.at.localeCompare(b.at));

const columns = list === "downloads" ? ["email", "at", "country", "build"] : ["email", "at", "source", "platform"];
console.log(columns.join(","));
for (const entry of entries) console.log(columns.map((column) => entry[column] ?? "").join(","));
console.error(`${entries.length} ${list}`);
