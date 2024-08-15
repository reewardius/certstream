# substream

substream is a python tool thath helps penetration testers and bug hunters collect and gather subdomains for their lists by connecting to the certstream firehose, watching for real subdomains, and adding them to a list for use with the above tools.

## Installation

```
git clone https://github.com/reewardius/certstream
```

## Recommended Python Version:

substream currently supports **Python 3**.  Stop using **Python 2**.  I suck at Python and even I know that.

* The recommended version for Python 3 is **3.8.x**

NOTE: There is currently an issue with a dependency and Python v3.9 so do not upgrade to that version for now as you will receive websockets errors until the dependency is updated.

## Dependencies:

Substr3am depends on the `certstream`, `requests`, `tldextract` python modules.

These dependencies can be installed using the requirements file:

- Installation on Windows:
```
c:\python\python.exe -m pip install -r requirements.txt
```
- Installation on Linux / MacOS:
```
sudo pip3 install -r requirements.txt
```

## Usage

* To only return results for a particular list of domains

```python3 substream.py -f google.com google.cn microsoft.com uber.com```

```python3 substream.py -F domains.txt```

* To return results only for a specific list of domains and send them to Telegram

```python3 substream.py -F domains.txt -t -ti <chatId> -ty <telegram-bot-http-api-token> ```
