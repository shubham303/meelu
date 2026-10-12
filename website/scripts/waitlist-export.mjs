/**
 * Dump the waitlist out of the R2 bucket as CSV.
 *
 *   node --env-file=.env.local scripts/waitlist-export.mjs > waitlist.csv
 *
 * Needs R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET.
 * One object per signup, keyed by a hash of the address, so the list is
 * already deduped. Oldest first.
 */
import { GetObjectCommand, ListObjectsV2Command, S3Client } from "@aws-sdk/client-s3";

const { R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET } = process.env;
if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY || !R2_BUCKET) {
  console.error("Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET.");
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
    new ListObjectsV2Command({ Bucket: R2_BUCKET, Prefix: "waitlist/", ContinuationToken: token }),
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

console.log("email,joined_at,source,platform");
for (const entry of entries) {
  console.log(`${entry.email},${entry.at},${entry.source ?? ""},${entry.platform ?? ""}`);
}
console.error(`${entries.length} signups`);
