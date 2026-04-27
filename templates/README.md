# README

Simple arXiv RSS feed filtering for key-words with toggleable sources and config saving


## Instructions

### Manual testing

`conda activate arxivfeed`
`python app.py`



### Stop the server

`launchctl unload ~/Library/LaunchAgents/com.arxivfeed.server.plist`

### Restart after code changes

```
launchctl unload ~/Library/LaunchAgents/com.arxivfeed.server.plist
launchctl load ~/Library/LaunchAgents/com.arxivfeed.server.plist
```

Check if its running:
`curl -s -o /dev/null -w "%{http_code}" http://localhost:5099`
    This should return 200.


### Check logs

```
tail -f ~/Library/Logs/arxivfeed.log
tail -f ~/Library/Logs/arxivfeed.err
```