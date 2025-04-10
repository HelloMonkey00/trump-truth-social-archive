# Trump Truth Social archive scraper

This repository contains a Python script that scrapes posts from Donald Trump's Truth Social account and stores them in JSON and CSV formats. The scraper runs hourly via a GitHub Actions workflow and updates an S3 archive to keep a historical record of the posts. 

## How it works

### Fetching data from Truth Social API

The script (`scraper.py`) fetches posts directly from the Truth Social API using a proxy service (`ScrapeOps`) to ensure successful requests.

- **Pagination support:** It requests up to 100 new posts in batches of 20.
- **Media extraction:** Any images or videos in a post are extracted and stored as an array of URLs.
- **Duplicate handling:** Before adding new posts, the script checks an existing archive to avoid duplicates.

## Data output format

The scraper outputs posts in JSON format with the following structure:

```json
[
  {
    "id": "114132050804394743",
    "created_at": "2025-03-09T10:41:28.605Z",
    "content": "Will be interviewed by Maria Bartiromo on Sunday Morning Futures at 10:00amET, enjoy! <span class=\"h-card\"><a href=\"https://truthsocial.com/@FoxNews\" class=\"u-url mention\">@<span>FoxNews</span></a></span>",
    "url": "https://truthsocial.com/@realDonaldTrump/114132050804394743",
    "media": [
      "https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/media_attachments/files/114/132/050/631/878/172/original/f0e7d14a580b0bc6.mp4"
    ],
    "replies_count": 925,
    "reblogs_count": 2938,
    "favourites_count": 13166
  },
  {
    "id": "114130744626893259",
    "created_at": "2025-03-09T05:09:17.893Z",
    "content": "",
    "url": "https://truthsocial.com/@realDonaldTrump/114130744626893259",
    "media": [
      "https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/media_attachments/files/114/130/744/449/958/273/original/56b8a2c4e789ede9.jpg"
    ],
    "replies_count": 2451,
    "reblogs_count": 3833,
    "favourites_count": 16848
  },
]
```

### Field descriptions

- **`id`** → The unique identifier for the post
- **`created_at`** → Timestamp when the post was made
- **`content`** → The text content of the post
- **`url`** → Direct link to the post on Truth Social
- **`media`** → An array of image and video URLs if the post contains media
- **`replies_count`** → Number of replies to Trump post
- **`reblogs_count`** → Number of re-posts, or re-truths, to Trump post
- **`favourites_count`** → Number of favorites to Trump post

## Docker Setup

This repository now includes Docker support for easy deployment. The container runs the scraper on a schedule and can send notifications to a Lark (Feishu) workspace.

### Using Docker Compose

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your credentials:
   ```
   SCRAPE_PROXY_KEY=your_scrapeops_api_key
   LARK_WEBHOOK_URL=your_lark_webhook_url
   HEALTH_CHECK_URL=your_health_check_webhook_url
   ```

3. Start the container:
   ```bash
   docker-compose up -d
   ```

### Cron Schedule

- The scraper runs every minute to fetch new posts
- When new posts are found, notifications are sent immediately

### Lark Notifications

The system now supports sending notifications to a Lark (Feishu) workspace when new Trump posts are detected. Notifications include:

- Post content
- Media links
- Engagement metrics (replies, reblogs, favorites)
- Direct link to the original post

To set up Lark notifications:

1. Create a Lark bot in your workspace and get the webhook URL
2. Add the webhook URL to your environment variables
3. The container will automatically send notifications when new posts are detected

### Health Checks

The system includes a health check feature that monitors for errors and sends alerts when:

- The system fails to fetch posts for a threshold number of times (currently 5)
- The target site may be blocking requests or changed its structure

Health alerts:
- Are limited to one alert per day to avoid notification spam
- Can be sent to a separate webhook URL for system administrators

## Testing Locally

The repository includes several test scripts to verify functionality before deployment:

### General Testing

The `test_locally.py` script provides a full simulation of the scraper's functionality:

```bash
# Run all tests
python test_locally.py

# Test only specific components
python test_locally.py --mode scrape  # Test only scraping
python test_locally.py --mode notify  # Test only notifications
python test_locally.py --mode error   # Test only error handling

# Keep test data for inspection
python test_locally.py --clean
```

### Lark Notification Testing

The `test_lark_notification.py` script tests the Lark notification functionality:

```bash
# First set your Lark webhook URL
export LARK_WEBHOOK_URL="your_lark_webhook_url"

# Run all notification tests
python test_lark_notification.py

# Test specific notification features
python test_lark_notification.py --test single  # Test single notification
python test_lark_notification.py --test media   # Test notification with media
python test_lark_notification.py --test batch   # Test batch notifications
python test_lark_notification.py --test dedup   # Test deduplication
```

### Health Check Testing

The `test_health_check.py` script tests the health check and error handling functionality:

```bash
# Run all health check tests
python test_health_check.py

# Test specific health check features
python test_health_check.py --test count      # Test error counting
python test_health_check.py --test limit      # Test daily alert limit
python test_health_check.py --test threshold  # Test error threshold alerts
```

## GitHub Actions automation

The scraper runs every four hours at 47 minutes past. It's using a GitHub Actions workflow and environment secrets for AWS and ScrapeOps. In addition to fetching the data, the workflow also copies it to a designated S3 bucket. 

*Note: I'm considering strategies now for periodically rehydrating the archive with updated engeagement analytics (re-posts, replies, etc.) so that we capture changes over time for popular posts.*

### Workflow steps

1. Clone the repository
2. Set up Python and install required dependencies
3. Run `scraper.py` to fetch the latest posts
4. Save new posts and update `truth_archive.json`
5. Upload the updated JSON file to an S3 bucket (`stilesdata.com/trump-truth-social-archive/`)
6. Commit and push changes back to GitHub

## Installation and running locally

To run the scraper manually on your machine:

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set environment variables

You'll need to export your ScrapeOps API key and AWS credentials:

```bash
export SCRAPE_PROXY_KEY="your_scrapeops_api_key"
export AWS_ACCESS_KEY_ID="your_aws_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret"
export LARK_WEBHOOK_URL="your_lark_webhook_url"      # Optional, for notifications
export HEALTH_CHECK_URL="your_health_check_url"      # Optional, for health monitoring
```

### Run the scraper

```bash
python scraper.py
```

This will fetch new posts and update `truth_archive.json` and `truth_archive.csv`.

### Send notifications manually

```bash
python send_lark_notification.py
```

This will check for new posts and send notifications to your configured Lark workspace.

## Logging

The system includes comprehensive logging:

- Logs are stored in `./data/logs/` directory
- Each component has its own log file with date-based naming
- Log files include timestamps, log levels, and detailed information
- All logs are also output to the console for real-time monitoring

## Data storage and access

- Historical posts are stored in an S3 bucket:
  - [`truth_archive.json`](https://stilesdata.com/trump-truth-social-archive/truth_archive.json)
  - [`truth_archive.csv`](https://stilesdata.com/trump-truth-social-archive/truth_archive.csv)

- The latest version of these files is also stored in this repo and updated regularly.

## Notes

This project is for archival and research purposes only. Use responsibly. It is not affiliated with my employer.

### Next steps and improvements:

- Better flags for original posts vs. retweets
- Better handling of media-only posts
- Improve media handling (support for more formats)
- Implement error logging for better monitoring
- Better analytics: Keywords, classification, etc. 
- Consider front-end display or Slack integration to help news teams monitor posts