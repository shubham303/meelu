from dataclasses import dataclass


def bullet_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    prefix = ""
    for raw in markdown.splitlines():
        if raw.startswith("## "):
            heading = raw[3:].strip()
            prefix = f"{heading}: " if heading.lower().startswith("avoid") else ""
        elif raw.startswith("- "):
            lines.append(prefix + raw[2:].strip())
        elif raw.startswith("  ") and lines:
            lines[-1] = f"{lines[-1]} {raw.strip()}"
    return lines


@dataclass(frozen=True)
class PlatformSeed:
    key: str
    label: str
    character_limit: int
    compose_url: str
    requires_media: bool
    default_instructions: str
    max_links: int | None = None
    max_hashtags: int | None = None
    max_media: int = 0
    allows_promotion: bool = True

    def rules(self) -> list[str]:
        return bullet_lines(self.default_instructions)


LINKEDIN_INSTRUCTIONS = """# Writing for LinkedIn

## Shape
- Open with one concrete sentence that could only be written by someone who
  did the thing. No throat-clearing, no "In today's fast-paced world".
- The first two lines are all anyone sees before "…more". Earn the click there
  or nowhere.
- Short paragraphs, one idea each, blank line between. Walls of text lose.
- 800–1,600 characters is the sweet spot. The limit is 3,000; needing it is
  usually a sign the post is two posts.
- Close with a real question or a clear takeaway — not "Thoughts? 👇".

## Voice
- First person, past tense, specific. "We cut onboarding from 6 steps to 2"
  beats "Streamlining onboarding is critical".
- Numbers, names and dates wherever they're true. Vagueness reads as bluffing.
- Say the uncomfortable part. The posts that land admit a cost, a mistake, or
  a tradeoff.

## Avoid
- Engagement bait: "Agree?", "Who else?", "Save this for later", follow-for-
  follow, fake polls.
- The broetry format — one. line. per. paragraph. for. drama.
- Emoji bullets and emoji section headers. At most one emoji, if any.
- Hashtag stuffing. Three at the end, or none.
- Anything that reads as if it were written by a language model: "delve",
  "leverage", "in today's landscape", "game-changer", "unlock", "supercharge",
  "it's not just X, it's Y".
- External links in the body when it can be avoided — LinkedIn suppresses
  reach on them. Put the link in the first comment and say so.

## Format facts
- 3,000 character hard limit.
- No markdown. Bold and italics do not render; asterisks show up literally.
- Line breaks survive; use them instead of formatting.
- @-mentions and #hashtags are live; plain URLs are auto-linked."""


INSTAGRAM_INSTRUCTIONS = """# Writing for Instagram

## The picture leads
- The image does the work; the caption explains, sharpens or undercuts it.
  Write the caption *to* the picture — if it would read the same against any
  other image, it isn't an Instagram caption.
- Say what the image is, for anyone who can't see it well. Then say why it's
  here.

## Shape
- The first line is the whole game — only about 125 characters show before
  "… more". Front-load it.
- 150–400 characters reads best. The limit is 2,200 and using it is almost
  always a mistake.
- Line breaks survive and are the only formatting you get. Use them.
- One clear ask at the end, if any: reply, save, or tap the link in bio.

## Voice
- Warmer and more personal than LinkedIn. First person, present tense.
- Specific beats clever. A real detail from the day it was taken lands better
  than a polished line.

## Avoid
- Links in the caption — they are not clickable. Say "link in bio" instead.
- Hashtag walls. Three to five relevant ones at the end, not thirty.
- Engagement bait ("double tap if…", "comment YES"), and follow-for-follow.
- Anything that reads as if a language model wrote it: "dive into",
  "game-changer", "unlock", "elevate your".
- Reposting someone's photo without credit.

## Format facts
- 2,200 character hard limit; roughly 125 shown before the fold.
- No markdown, no clickable links, no bold or italics.
- An image is required — a caption on its own is not a post.
- Square (1080×1080) or portrait (1080×1350) crops use the most feed space."""


TWITTER_INSTRUCTIONS = """# Writing for X

## Shape
- One idea per post. If it needs a second idea, it needs a second post.
- 280 characters is the whole canvas on a free account. Write to ~250 so a
  quote-post or a handle still fits.
- Front-load the point. The first seven or eight words decide whether anyone
  reads the rest as they scroll past.
- A thread is for a sequence that genuinely has parts. Do not chop one thought
  into five posts for reach.

## Voice
- Flat, declarative, unhurried. The register that works here is someone saying
  a true thing plainly, not someone performing.
- Concrete nouns and real numbers. "Cut the build from 90s to 11s" travels;
  "massively improved build performance" does not.
- It is fine to be blunt. It is not fine to be snide about a named person or
  company.

## Avoid
- Thread bait: "a thread 🧵", "1/", "bookmark this", "read to the end".
- Hashtags. They read as marketing here — one, at most, and usually none.
- Opening with "Just shipped" or "Excited to announce" unless something was
  genuinely just shipped or announced.
- Rhetorical-question openers ("Ever wondered why…?").
- Anything that reads as if a language model wrote it: "game-changer",
  "unlock", "in today's landscape", "it's not just X, it's Y".

## Format facts
- 280 characters on a free account. Paid accounts allow 25,000 — do not rely
  on it; the post has to survive on a free account.
- Links cost characters and are shortened, but still spend roughly 23.
- No markdown. Line breaks survive.
- Up to four images, or one video — never both in the same post."""


THREADS_INSTRUCTIONS = """# Writing for Threads

## Shape
- 500 characters, hard. This is the defining constraint: it is longer than X
  and much shorter than LinkedIn, and copy written for either reads wrong here.
- One thought, finished. Threads rewards a complete small idea over an
  intriguing fragment.
- Longer copy splits into a chain of posts, each one able to stand alone.

## Voice
- Conversational, first person, present tense. Closer to talking than writing.
- Warmer and less transactional than X. Opinions land better than takes.
- Asking something real gets real replies; the audience here is genuinely
  chattier than on other feeds.

## Avoid
- Cross-posting X copy unchanged. It reads clipped and cold.
- Hashtags — Threads barely uses them and they look imported.
- Engagement bait, follow-for-follow, and "drop a 🔥 if…".
- Links as the whole point of the post. Say the thing, then link.

## Format facts
- 500 character hard limit, strictly enforced.
- No markdown; line breaks survive.
- Text-only posts are fine. Up to 20 images, or one video.
- A published post cannot be edited — get it right before it goes."""


BLUESKY_INSTRUCTIONS = """# Writing for Bluesky

## Shape
- 300 characters. Shorter than X, and the tightest budget of any channel here.
- Say the thing in the first line; there is no room for a wind-up.
- A chain is acceptable for a genuine sequence, but a single well-cut post is
  what the feed rewards.

## Voice
- Plain, curious, a little more informal than X. The culture is early-internet:
  people read carefully and reply in good faith.
- Craft and process notes do unusually well — how something was made, what
  broke, what you changed your mind about.
- Self-promotion is tolerated when it is specific and occasional.

## Avoid
- Marketing cadence of any kind. It is spotted instantly here.
- Hashtags — the network does not lean on them.
- Engagement bait and growth-hacking language.
- Reposting a press release as if it were a thought.

## Format facts
- 300 graphemes, not bytes — an emoji or a combining sequence counts as one.
- No markdown; line breaks survive.
- Up to four images (1 MB each) or one video — never both.
- A bare URL auto-generates a link card, but a link card and an attached image
  are mutually exclusive. Pick one."""


FACEBOOK_INSTRUCTIONS = """# Writing for Facebook

## Shape
- The nominal limit is enormous; the real one is about three lines before
  "See more". Put the whole point above that fold.
- 80–250 characters is where a post reads best. A long post here is a blog
  entry in the wrong place.
- One image with a short caption outperforms a wall of text almost every time.

## Voice
- Plain and human, addressed to people who already know you — Facebook's reach
  is mostly to an existing audience rather than a discovery feed.
- Local, specific and timely does well: an opening, a change of hours, a photo
  from this morning.
- Warm without being saccharine. First person plural is natural here.

## Avoid
- Engagement bait ("like if you agree", "tag a friend", "comment YES") — Meta
  actively down-ranks it.
- Hashtag stuffing. One or two, or none.
- Posting the same copy as LinkedIn. The audience and register are different.
- Anything that reads as if a language model wrote it.

## Format facts
- 63,206 character limit on a feed post — a technical ceiling, not a target.
- No markdown. Line breaks survive.
- Up to 10 images, or one video, never mixed.
- Posting goes to a Page, and the Page must be chosen when connecting."""


TIKTOK_INSTRUCTIONS = """# Writing for TikTok

## Shape
- The caption is a caption, not the post. The media carries it; the words give
  it context or a hook.
- One line is usually right. The first ~50 characters show before the fold.
- Say what the viewer is looking at, or the reason to keep watching. Not both.

## Voice
- Casual, present tense, unpolished. Anything that sounds like advertising
  copy dies here faster than anywhere else.
- Speak as a person, not a brand. "I" and "we" over the company name.
- A genuine hook — a question, a surprising number, an admission — beats a
  clever line.

## Avoid
- Corporate register of any kind.
- Hashtag walls. Three or four relevant ones, at the end.
- Recycling an Instagram caption verbatim; the tone is different.
- Promising something the media doesn't deliver.

## Format facts
- 2,200 character limit on the caption.
- Media is required — TikTok takes no text-only post.
- Meelu attaches one image, which posts as a photo post. TikTok's photo posts
  accept jpg and gif; a video has to be uploaded on TikTok itself.
- Comments and Duet/Stitch are disabled by default on API posts."""


PINTEREST_INSTRUCTIONS = """# Writing for Pinterest

## The picture is the product
- Pinterest is a search engine with pictures. The image decides whether the pin
  is seen at all; the words decide whether it is found.
- Vertical images (2:3, e.g. 1000×1500) take far more feed than square ones.

## Shape
- Write the description as a person would search for the thing, in plain words,
  in a full sentence or two. Keyword stuffing reads as spam and ranks worse.
- 100–200 characters is plenty of the 500 available.
- Say what it is, who it is for, and what they would do with it.

## Voice
- Useful and concrete, not clever. Pinterest users are planning something.
- Present tense, second person is natural: "Fold the edge under before the
  second bake."

## Avoid
- Hashtags — Pinterest deprecated them and they clutter the description.
- Time-bound copy ("this week only"). Pins surface for years.
- Engagement bait; there is no engagement culture here to bait.

## Format facts
- Description 500 characters; a pin title is 100.
- An image is required, and exactly one — no carousels through the API.
- A pin is saved to a board, chosen when the account is connected.
- Note: Meelu's post title is an internal calendar label and is not published,
  so the description has to carry the pin on its own."""


TELEGRAM_INSTRUCTIONS = """# Writing for Telegram

## Shape
- A channel post is read like a message, not a broadcast. Get to it in the
  first sentence.
- Short paragraphs with blank lines between. Long unbroken text is hard to read
  in a chat client.
- One post, one purpose. Subscribers see every post — frequency costs more here
  than anywhere else.

## Voice
- Direct and informative. Telegram audiences opt in deliberately and want the
  substance, not the framing.
- Links are welcome and clickable, unlike most social feeds. Use them.
- Announcements, changelogs and long-form notes all fit here naturally.

## Avoid
- Marketing cadence and emoji headers.
- Posting several times a day — it reads as noise and costs subscribers.
- Burying the news under a preamble.

## Format facts
- 4,096 characters for a text-only post — **but only 1,024 when an image is
  attached.** Attaching a picture cuts the budget by three quarters; write to
  the smaller number whenever the post carries one.
- Line breaks survive. Plain URLs are clickable.
- Posting goes to a channel or group, chosen when connecting, and the bot has
  to be a member of it (administrator, preferably)."""


GOOGLE_BUSINESS_INSTRUCTIONS = """# Writing for a Google Business Profile

## Shape
- This appears next to the business in Search and Maps, to someone who is
  deciding whether to visit or call. Write for that moment.
- Lead with the concrete fact: what is new, what is on, what has changed.
- 150–300 characters of the 1,500 available. Nobody reads a long one.
- End with the practical detail — hours, address nuance, what to ask for.

## Voice
- Plain, factual, local. First person plural as the business.
- Specific beats promotional: "New winter hours: 8–4, Tue to Sat" is a better
  post than "Exciting news about our hours!".
- Accuracy matters more than tone here; this is closer to a listing than a feed.

## Avoid
- Marketing language, superlatives and exclamation marks.
- Anything time-sensitive without the date in the text — posts linger.
- Phone numbers or URLs stuffed into the body; the profile already carries them.
- Claims about pricing or availability that will age badly.

## Format facts
- 1,500 character limit on the post summary.
- One image, jpg or png, minimum 400×300 (1200×900 recommended, 4:3). No video.
- Posts go to one business location, chosen when the account is connected."""


WEBSITE_INSTRUCTIONS = """# Publishing to the website

- This is the long-form home of the piece: full article, headings, internal
  links to related pages on the site, one clear call to action at the end.
- Title under 60 characters and a first paragraph that answers the search
  intent directly; the rest of the piece earns the scroll.
- Markdown renders as written. Use H2/H3 headings, short paragraphs, lists
  where the content is actually a list.
- Link to other pages on the site by path. External links open in the same
  tab; link only to sources that support a specific claim.
- Every claim with a number needs a source or a first-hand basis."""


PLATFORM_SEEDS: list[PlatformSeed] = [
    PlatformSeed(
        key="linkedin",
        label="LinkedIn",
        character_limit=3000,
        compose_url="https://www.linkedin.com/feed/?shareActive=true",
        requires_media=False,
        max_links=1,
        max_hashtags=3,
        max_media=9,
        default_instructions=LINKEDIN_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="instagram",
        label="Instagram",
        character_limit=2200,
        compose_url="https://www.instagram.com/",
        requires_media=True,
        max_links=0,
        max_hashtags=5,
        max_media=10,
        default_instructions=INSTAGRAM_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="twitter",
        label="X",
        character_limit=280,
        compose_url="https://x.com/compose/post",
        requires_media=False,
        max_links=1,
        max_hashtags=2,
        max_media=4,
        default_instructions=TWITTER_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="threads",
        label="Threads",
        character_limit=500,
        compose_url="https://www.threads.net/",
        requires_media=False,
        max_links=1,
        max_hashtags=1,
        max_media=10,
        default_instructions=THREADS_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="bluesky",
        label="Bluesky",
        character_limit=300,
        compose_url="https://bsky.app/",
        requires_media=False,
        max_links=1,
        max_hashtags=2,
        max_media=4,
        default_instructions=BLUESKY_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="facebook",
        label="Facebook",
        character_limit=63206,
        compose_url="https://www.facebook.com/",
        requires_media=False,
        max_links=1,
        max_hashtags=2,
        max_media=10,
        default_instructions=FACEBOOK_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="tiktok",
        label="TikTok",
        character_limit=2200,
        compose_url="https://www.tiktok.com/upload",
        requires_media=True,
        max_links=0,
        max_hashtags=4,
        max_media=1,
        default_instructions=TIKTOK_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="pinterest",
        label="Pinterest",
        character_limit=500,
        compose_url="https://www.pinterest.com/pin-builder/",
        requires_media=True,
        max_links=1,
        max_hashtags=3,
        max_media=1,
        default_instructions=PINTEREST_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="telegram",
        label="Telegram",
        character_limit=4096,
        compose_url="https://web.telegram.org/",
        requires_media=False,
        max_links=2,
        max_hashtags=0,
        max_media=10,
        default_instructions=TELEGRAM_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="google_business",
        label="Google Business",
        character_limit=1500,
        compose_url="https://business.google.com/posts",
        requires_media=False,
        max_links=1,
        max_hashtags=0,
        max_media=1,
        default_instructions=GOOGLE_BUSINESS_INSTRUCTIONS,
    ),
    PlatformSeed(
        key="website",
        label="Website",
        character_limit=0,
        compose_url="",
        requires_media=False,
        default_instructions=WEBSITE_INSTRUCTIONS,
        max_links=None,
        max_hashtags=0,
        max_media=20,
    ),
]

SEEDS_BY_KEY: dict[str, PlatformSeed] = {seed.key: seed for seed in PLATFORM_SEEDS}
