![Whoogle Search](https://raw.githubusercontent.com/koval01/whoogle-search-kdev/main/docs/banner.png)

[![Latest Release](https://img.shields.io/github/v/release/koval01/whoogle-search-kdev)](https://github.com/koval01/whoogle-search-kdev/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![tests](https://github.com/koval01/whoogle-search-kdev/actions/workflows/tests.yml/badge.svg)](https://github.com/koval01/whoogle-search-kdev/actions/workflows/tests.yml)
[![buildx](https://github.com/koval01/whoogle-search-kdev/actions/workflows/buildx.yml/badge.svg)](https://github.com/koval01/whoogle-search-kdev/actions/workflows/buildx.yml)
[![codebeat badge](https://codebeat.co/badges/e96cada2-fb6f-4528-8285-7d72abd74e8d)](https://codebeat.co/projects/github-com-koval01-shoogle-master)
[![Docker Pulls](https://img.shields.io/docker/pulls/koval01/whoogle-search-kdev)](https://hub.docker.com/r/koval01/whoogle-search-kdev)

Get Google search results, but without any ads, javascript, AMP links, cookies, or IP address tracking. Easily deployable in one click as a Docker app, and customizable with a single config file. Quick and simple to implement as a primary search engine replacement on both desktop and mobile.

Contents
1. [Features](#features)
2. [Dependencies](#dependencies)
3. [Install/Deploy](#install)
    1. [Heroku Quick Deploy](#a-heroku-quick-deploy)
    2. [Repl.it](#b-replit)
    3. [Fly.io](#c-flyio)
    4. [pipx](#d-pipx)
    5. [pip](#e-pip)
    6. [Manual](#f-manual)
    7. [Docker](#g-manual-docker)
    8. [Arch/AUR](#arch-linux--arch-based-distributions)
    9. [Helm/Kubernetes](#helm-chart-for-kubernetes)
4. [Environment Variables and Configuration](#environment-variables)
5. [Usage](#usage)
6. [Extra Steps](#extra-steps)
    1. [Set Primary Search Engine](#set-whoogle-as-your-primary-search-engine)
    2. [Prevent Downtime (Heroku Only)](#prevent-downtime-heroku-only)
    3. [Manual HTTPS Enforcement](#https-enforcement)
    4. [Using with Firefox Containers](#using-with-firefox-containers)
    5. [Reverse Proxying](#reverse-proxying)
        1. [Nginx](#nginx)
7. [Contributing](#contributing)
8. [FAQ](#faq)
9. [Public Instances](#public-instances)
10. [Screenshots](#screenshots)
11. Mirrors (read-only)
    1. [GitLab](https://gitlab.com/koval01/whoogle-search-kdev)
    2. [Gogs](https://gogs.koval01.com/koval01/whoogle-search-kdev)

## Features
- No ads or sponsored content
- No JavaScript\*
- No cookies\*\*
- No tracking/linking of your personal IP address\*\*\*
- No AMP links
- No URL tracking tags (i.e. utm=%s)
- No referrer header
- Tor and HTTP/SOCKS proxy support
- Autocomplete/search suggestions
- POST request search and suggestion queries (when possible)
- View images at full res without site redirect (currently mobile only)
- Light/Dark/System theme modes (with support for [custom CSS theming](https://github.com/koval01/whoogle-search-kdev/wiki/User-Contributed-CSS-Themes))
- Randomly generated User Agent
- Easy to install/deploy
- DDG-style bang (i.e. `!<tag> <query>`) searches
- Optional location-based searching (i.e. results near \<city\>)
- Optional NoJS mode to view search results in a separate window with JavaScript blocked

<sup>*No third party JavaScript. Whoogle can be used with JavaScript disabled, but if enabled, uses JavaScript for things like presenting search suggestions.</sup>

<sup>**No third party cookies. Whoogle uses server side cookies (sessions) to store non-sensitive configuration settings such as theme, language, etc. Just like with JavaScript, cookies can be disabled and not affect Whoogle's search functionality.</sup>

<sup>***If deployed to a remote server, or configured to send requests through a VPN, Tor, proxy, etc.</sup>

## Dependencies
If using Heroku Quick Deploy, **you can skip this section**.

- Docker ([Windows](https://docs.docker.com/docker-for-windows/install/), [macOS](https://docs.docker.com/docker-for-mac/install/), [Ubuntu](https://docs.docker.com/engine/install/ubuntu/), [other Linux distros](https://docs.docker.com/engine/install/binaries/))
  - Only needed if you intend on deploying the app as a Docker image
- [Python3](https://www.python.org/downloads/)
- `libcurl4-openssl-dev` and `libssl-dev`
  - macOS: `brew install openssl curl-openssl`
  - Ubuntu: `sudo apt-get install -y libcurl4-openssl-dev libssl-dev`
  - Arch: `pacman -S curl openssl`

## Install
There are a few different ways to begin using the app, depending on your preferences:

### A) [Heroku Quick Deploy](https://heroku.com/about)
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/koval01/whoogle-search-kdev/tree/main)

Provides:
- Free deployment of app
- Free HTTPS url (https://\<your app name\>.herokuapp.com)
- Downtime after periods of inactivity \([solution](https://github.com/koval01/whoogle-search-kdev#prevent-downtime-heroku-only)\)

Notes:
- Requires a (free) Heroku account
- Sometimes has issues with auto-redirecting to `https`. Make sure to navigate to the `https` version of your app before adding as a default search engine.

### B) [Repl.it](https://repl.it)
[![Run on Repl.it](https://repl.it/badge/github/koval01/whoogle-search-kdev)](https://repl.it/github/koval01/whoogle-search-kdev)

*Note: Requires a (free) Replit account*

Provides:
- Free deployment of app
- Free HTTPS url (https://\<app name\>.\<username\>\.repl\.co)
    - Supports custom domains
- Downtime after periods of inactivity \([solution 1](https://repl.it/talk/ask/use-this-pingmat1replco-just-enter/28821/101298), [solution 2](https://repl.it/talk/learn/How-to-use-and-setup-UptimeRobot/9003)\)

### C) [Fly.io](https://fly.io)

You will need a **PAID** [Fly.io](https://fly.io) account to deploy Whoogle.

#### Install the CLI: https://fly.io/docs/hands-on/installing/

#### Deploy the app

```bash
flyctl auth login
flyctl launch --image koval01/whoogle-search-kdev:latest
```

Your app is now available at `https://<app-name>.fly.dev`.

### D) [pipx](https://github.com/pipxproject/pipx#install-pipx)
Persistent install:

`pipx install git+https://github.com/koval01/whoogle-search-kdev.git`

Sandboxed temporary instance:

`pipx run --spec git+https://github.com/koval01/whoogle-search-kdev.git whoogle-search-kdev`

### E) pip
`pip install whoogle-search-kdev`

```bash
$ whoogle-search-kdev --help
usage: whoogle-search-kdev [-h] [--port <port number>] [--host <ip address>] [--debug] [--https-only] [--userpass <username:password>]
                      [--proxyauth <username:password>] [--proxytype <socks4|socks5|http>] [--proxyloc <location:port>]

Whoogle Search console runner

optional arguments:
  -h, --help            Show this help message and exit
  --port <port number>  Specifies a port to run on (default 5000)
  --host <ip address>   Specifies the host address to use (default 127.0.0.1)
  --debug               Activates debug mode for the server (default False)
  --https-only          Enforces HTTPS redirects for all requests
  --userpass <username:password>
                        Sets a username/password basic auth combo (default None)
  --proxyauth <username:password>
                        Sets a username/password for a HTTP/SOCKS proxy (default None)
  --proxytype <socks4|socks5|http>
                        Sets a proxy type for all connections (default None)
  --proxyloc <location:port>
                        Sets a proxy location for all connections (default None)
```
See the [available environment variables](#environment-variables) for additional configuration.

### F) Manual

*Note: `Content-Security-Policy` headers can be sent by Whoogle if you set `WHOOGLE_CSP`.*

Clone the repo and run the following commands to start the app in a local-only environment:

```bash
git clone https://github.com/koval01/whoogle-search-kdev.git
cd whoogle-search-kdev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run
```
See the [available environment variables](#environment-variables) for additional configuration.

#### systemd Configuration
After building the virtual environment, you can add something like the following to `/lib/systemd/system/whoogle.service` to set up a Whoogle Search systemd service:

```ini
[Unit]
Description=Whoogle

[Service]
# Basic auth configuration, uncomment to enable
#Environment=WHOOGLE_USER=<username>
#Environment=WHOOGLE_PASS=<password>
# Proxy configuration, uncomment to enable
#Environment=WHOOGLE_PROXY_USER=<proxy username>
#Environment=WHOOGLE_PROXY_PASS=<proxy password>
#Environment=WHOOGLE_PROXY_TYPE=<proxy type (http|https|proxy4|proxy5)
#Environment=WHOOGLE_PROXY_LOC=<proxy host/ip>
# Site alternative configurations, uncomment to enable
# Note: If not set, the feature will still be available
# with default values.
#Environment=WHOOGLE_ALT_TW=farside.link/nitter
#Environment=WHOOGLE_ALT_YT=farside.link/invidious
#Environment=WHOOGLE_ALT_IG=farside.link/bibliogram/u
#Environment=WHOOGLE_ALT_RD=farside.link/libreddit
#Environment=WHOOGLE_ALT_MD=farside.link/scribe
#Environment=WHOOGLE_ALT_TL=farside.link/lingva
#Environment=WHOOGLE_ALT_IMG=farside.link/rimgo
#Environment=WHOOGLE_ALT_WIKI=farside.link/wikiless
#Environment=WHOOGLE_ALT_IMDB=farside.link/libremdb
#Environment=WHOOGLE_ALT_QUORA=farside.link/quetre
# Load values from dotenv only
#Environment=WHOOGLE_DOTENV=1
Type=simple
User=<username>
# If installed as a package, add:
ExecStart=<python_install_dir>/python3 <whoogle_install_dir>/whoogle-search-kdev --host 127.0.0.1 --port 5000
# For example:
# ExecStart=/usr/bin/python3 /home/my_username/.local/bin/whoogle-search-kdev --host 127.0.0.1 --port 5000
# Otherwise if running the app from source, add:
ExecStart=<whoogle_repo_dir>/run
# For example:
# ExecStart=/var/www/whoogle-search-kdev/run
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3
SyslogIdentifier=whoogle

[Install]
WantedBy=multi-user.target
```
Then,
```
sudo systemctl daemon-reload
sudo systemctl enable whoogle
sudo systemctl start whoogle
```

#### Tor Configuration *optional*
If routing your request through Tor you will need to make the following adjustments.
Due to the nature of interacting with Google through Tor we will need to be able to send signals to Tor and therefore authenticate with it.

There are two authentication methods, password and cookie. You will need to make changes to your torrc:
  * Cookie
    1. Uncomment or add the following lines in your torrc:
       - `ControlPort 9051`
       - `CookieAuthentication 1`
       - `DataDirectoryGroupReadable 1`
       - `CookieAuthFileGroupReadable 1`

    2. Make the tor auth cookie readable:
       - This is assuming that you are using a dedicated user to run whoogle. If you are using a different user replace `whoogle` with that user.

       1. `chmod tor:whoogle /var/lib/tor`
       2. `chmod tor:whoogle /var/lib/tor/control_auth_cookie`

    3. Restart the tor service:
       - `systemctl restart tor`

    4. Set the Tor environment variable to 1, `WHOOGLE_CONFIG_TOR`. Refer to the [Environment Variables](#environment-variables) section for more details.
       - This may be added in the systemd unit file or env file `WHOOGLE_CONFIG_TOR=1`

  * Password
    1. Run this command:
       - `tor --hash-password {Your Password Here}`; put your password in place of `{Your Password Here}`.
       - Keep the output of this command, you will be placing it in your torrc.
       - Keep the password input of this command, you will be using it later.

    2. Uncomment or add the following lines in your torrc:
       - `ControlPort 9051`
       - `HashedControlPassword {Place output here}`; put the output of the previous command in place of `{Place output here}`.

    3. Now take the password from the first step and place it in the control.conf file within the whoogle working directory, ie. [misc/tor/control.conf](misc/tor/control.conf)
       - If you want to place your password file in a different location set this location with the `WHOOGLE_TOR_CONF` environment variable. Refer to the [Environment Variables](#environment-variables) section for more details.

    4. Heavily restrict access to control.conf to only be readable by the user running whoogle:
       - `chmod 400 control.conf`

    5. Finally set the Tor environment variable and use password variable to 1, `WHOOGLE_CONFIG_TOR` and `WHOOGLE_TOR_USE_PASS`. Refer to the [Environment Variables](#environment-variables) section for more details.
       - These may be added to the systemd unit file or env file:
          - `WHOOGLE_CONFIG_TOR=1`
          - `WHOOGLE_TOR_USE_PASS=1`

### G) Manual (Docker)
1. Ensure the Docker daemon is running, and is accessible by your user account
  - To add user permissions, you can execute `sudo usermod -aG docker yourusername`
  - Running `docker ps` should return something besides an error. If you encounter an error saying the daemon isn't running, try `sudo systemctl start docker` (Linux) or ensure the docker tool is running (Windows/macOS).
2. Clone and deploy the docker app using a method below:

#### Docker CLI

Through Docker Hub:
```bash
docker pull koval01/whoogle-search-kdev
docker run --publish 5000:5000 --detach --name whoogle-search-kdev koval01/whoogle-search-kdev:latest
```

or with docker-compose:

```bash
git clone https://github.com/koval01/whoogle-search-kdev.git
cd whoogle-search-kdev
docker-compose up
```

or by building yourself:

```bash
git clone https://github.com/koval01/whoogle-search-kdev.git
cd whoogle-search-kdev
docker build --tag whoogle-search-kdev:1.0 .
docker run --publish 5000:5000 --detach --name whoogle-search-kdev whoogle-search-kdev:1.0
```

Optionally, you can also enable some of the following environment variables to further customize your instance:

```bash
docker run --publish 5000:5000 --detach --name whoogle-search-kdev \
  -e WHOOGLE_USER=username \
  -e WHOOGLE_PASS=password \
  -e WHOOGLE_PROXY_USER=username \
  -e WHOOGLE_PROXY_PASS=password \
  -e WHOOGLE_PROXY_TYPE=socks5 \
  -e WHOOGLE_PROXY_LOC=ip \
  whoogle-search-kdev:1.0
```

And kill with: `docker rm --force whoogle-search-kdev`

#### Using [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
```bash
heroku login
heroku container:login
git clone https://github.com/koval01/whoogle-search-kdev.git
cd whoogle-search-kdev
heroku create
heroku container:push web
heroku container:release web
heroku open
```

This series of commands can take a while, but once you run it once, you shouldn't have to run it again. The final command, `heroku open` will launch a tab in your web browser, where you can test out Whoogle and even [set it as your primary search engine](https://github.com/koval01/whoogle#set-whoogle-as-your-primary-search-engine).
You may also edit environment variables from your app’s Settings tab in the Heroku Dashboard.

#### Arch Linux & Arch-based Distributions
There is an [AUR package available](https://aur.archlinux.org/packages/whoogle-git/), as well as a pre-built and daily updated package available at [Chaotic-AUR](https://chaotic.cx).

#### Helm chart for Kubernetes
To use the Kubernetes Helm Chart:
1. Ensure you have [Helm](https://helm.sh/docs/intro/install/) `>=3.0.0` installed
2. Clone this repository
3. Update [charts/whoogle/values.yaml](./charts/whoogle/values.yaml) as desired
4. Run `helm install whoogle ./charts/whoogle`

#### Using your own server, or alternative container deployment
There are other methods for deploying docker containers that are well outlined in [this article](https://rollout.io/blog/the-shortlist-of-docker-hosting/), but there are too many to describe set up for each here. Generally it should be about the same amount of effort as the Heroku deployment.

Depending on your preferences, you can also deploy the app yourself on your own infrastructure. This route would require a few extra steps:
  - A server (I personally recommend [Digital Ocean](https://www.digitalocean.com/pricing/) or [Linode](https://www.linode.com/pricing/), their cheapest tiers will work fine)
  - Your own URL (I suppose this is optional, but recommended)
  - SSL certificates (free through [Let's Encrypt](https://letsencrypt.org/getting-started/))
  - A bit more experience or willingness to work through issues

## Environment Variables
There are a few optional environment variables available for customizing a Whoogle instance. These can be set manually, or copied into `whoogle.env` and enabled for your preferred deployment method:

- Local runs: Set `WHOOGLE_DOTENV=1` before running
- With `docker-compose`: Uncomment the `env_file` option
- With `docker build/run`: Add `--env-file ./whoogle.env` to your command

| Variable             | Description                                                                               |
| -------------------- | ----------------------------------------------------------------------------------------- |
| WHOOGLE_URL_PREFIX   | The URL prefix to use for the whoogle instance (i.e. "/whoogle")                          |
| WHOOGLE_DOTENV       | Load environment variables in `whoogle.env`                                               |
| WHOOGLE_USER         | The username for basic auth. WHOOGLE_PASS must also be set if used.                       |
| WHOOGLE_PASS         | The password for basic auth. WHOOGLE_USER must also be set if used.                       |
| WHOOGLE_PROXY_USER   | The username of the proxy server.                                                         |
| WHOOGLE_PROXY_PASS   | The password of the proxy server.                                                         |
| WHOOGLE_PROXY_TYPE   | The type of the proxy server. Can be "socks5", "socks4", or "http".                       |
| WHOOGLE_PROXY_LOC    | The location of the proxy server (host or ip).                                            |
| EXPOSE_PORT          | The port where Whoogle will be exposed.                                                   |
| HTTPS_ONLY           | Enforce HTTPS. (See [here](https://github.com/koval01/whoogle-search-kdev#https-enforcement)) |
| WHOOGLE_ALT_TW       | The twitter.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_YT       | The youtube.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_IG       | The instagram.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_RD       | The reddit.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_TL       | The Google Translate alternative to use. This is used for all "translate ____" searches.  Set to "" to disable. |
| WHOOGLE_ALT_MD       | The medium.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_IMG      | The imgur.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_WIKI     | The wikipedia.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_ALT_IMDB     | The imdb.com alternative to use when site alternatives are enabled in the config. Set to "" to disable.  |
| WHOOGLE_ALT_QUORA    | The quora.com alternative to use when site alternatives are enabled in the config. Set to "" to disable. |
| WHOOGLE_AUTOCOMPLETE | Controls visibility of autocomplete/search suggestions. Default on -- use '0' to disable. |
| WHOOGLE_MINIMAL      | Remove everything except basic result cards from all search queries.                      |
| WHOOGLE_CSP          | Sets a default set of 'Content-Security-Policy' headers                                   |
| WHOOGLE_RESULTS_PER_PAGE          | Set the number of results per page                                           |
| WHOOGLE_TOR_SERVICE  | Enable/disable the Tor service on startup. Default on -- use '0' to disable.              |
| WHOOGLE_TOR_USE_PASS | Use password authentication for tor control port. |
| WHOOGLE_TOR_CONF | The absolute path to the config file containing the password for the tor control port. Default: ./misc/tor/control.conf WHOOGLE_TOR_PASS must be 1 for this to work.|

### Config Environment Variables
These environment variables allow setting default config values, but can be overwritten manually by using the home page config menu. These allow a shortcut for destroying/rebuilding an instance to the same config state every time.

| Variable                             | Description                                                     |
| ------------------------------------ | --------------------------------------------------------------- |
| WHOOGLE_CONFIG_DISABLE               | Hide config from UI and disallow changes to config by client    |
| WHOOGLE_CONFIG_COUNTRY               | Filter results by hosting country                               |
| WHOOGLE_CONFIG_LANGUAGE              | Set interface language                                          |
| WHOOGLE_CONFIG_SEARCH_LANGUAGE       | Set search result language                                      |
| WHOOGLE_CONFIG_BLOCK                 | Block websites from search results (use comma-separated list)   |
| WHOOGLE_CONFIG_THEME                 | Set theme mode (light, dark, or system)                         |
| WHOOGLE_CONFIG_SAFE                  | Enable safe searches                                            |
| WHOOGLE_CONFIG_ALTS                  | Use social media site alternatives (nitter, invidious, etc)     |
| WHOOGLE_CONFIG_NEAR                  | Restrict results to only those near a particular city           |
| WHOOGLE_CONFIG_TOR                   | Use Tor routing (if available)                                  |
| WHOOGLE_CONFIG_NEW_TAB               | Always open results in new tab                                  |
| WHOOGLE_CONFIG_VIEW_IMAGE            | Enable View Image option                                        |
| WHOOGLE_CONFIG_GET_ONLY              | Search using GET requests only                                  |
| WHOOGLE_CONFIG_URL                   | The root url of the instance (`https://<your url>/`)            |
| WHOOGLE_CONFIG_STYLE                 | The custom CSS to use for styling (should be single line)       |
| WHOOGLE_CONFIG_PREFERENCES_ENCRYPTED | Encrypt preferences token, requires preferences key             |
| WHOOGLE_CONFIG_PREFERENCES_KEY       | Key to encrypt preferences in URL (REQUIRED to show url)        |

## Usage
Same as most search engines, with the exception of filtering by time range.

To filter by a range of time, append ":past <time>" to the end of your search, where <time> can be `hour`, `day`, `month`, or `year`. Example: `coronavirus updates :past hour`

## Extra Steps
### Set Whoogle as your primary search engine
*Note: If you're using a reverse proxy to run Whoogle Search, make sure the "Root URL" config option on the home page is set to your URL before going through these steps.*

Browser settings:
  - Firefox (Desktop)
    - Version 89+
      - Navigate to your app's url, right click the address bar, and select "Add Search Engine".
    - Previous versions
      - Navigate to your app's url, and click the 3 dot menu in the address bar. At the bottom, there should be an option to "Add Search Engine".
    - Once you've added the new search engine, open your Firefox Preferences menu, click "Search" in the left menu, and use the available dropdown to select "Whoogle" from the list.
    - **Note**: If your Whoogle instance uses Firefox Containers, you'll need to [go through the steps here](#using-with-firefox-containers) to get it working properly.
  - Firefox (iOS)
    - In the mobile app Settings page, tap "Search" within the "General" section. There should be an option titled "Add Search Engine" to select. It should prompt you to enter a title and search query url - use the following elements to fill out the form:
      - Title: "Whoogle"
      - URL: `http[s]://\<your whoogle url\>/search?q=%s`
  - Firefox (Android)
    - Version <79.0.0
      - Navigate to your app's url
      - Long-press on the search text field
      - Click the "Add Search Engine" menu item
        - Select a name and click ok
      - Click the 3 dot menu in the top right
      - Navigate to the settings menu and select the "Search" sub-menu
      - Select Whoogle and press "Set as default"
    - Version >=79.0.0
      - Click the 3 dot menu in the top right
      - Navigate to the settings menu and select the "Search" sub-menu
      - Click "Add search engine"
      - Select the 'Other' radio button
        - Name: "Whoogle"
        - Search string to use: `https://\<your whoogle url\>/search?q=%s`
  - [Alfred](https://www.alfredapp.com/) (Mac OS X)
	  1. Go to `Alfred Preferences` > `Features` > `Web Search` and click `Add Custom Search`. Then configure these settings
		   - Search URL: `https://\<your whoogle url\>/search?q={query}
		   - Title: `Whoogle for '{query}'` (or whatever you want)
		   - Keyword: `whoogle`

	  2. Go to `Default Results` and click the `Setup fallback results` button. Click `+` and add Whoogle, then  drag it to the top.
  - Chrome/Chromium-based Browsers
    - Automatic
      - Visit the home page of your Whoogle Search instance -- this will automatically add the search engine if the [requirements](https://www.chromium.org/tab-to-search/) are met (GET request, no OnSubmit script, no path). If not, you can add it manually.
    - Manual
      - Under search engines > manage search engines > add, manually enter your Whoogle instance details with a `<whoogle url>/search?q=%s` formatted search URL.

### Prevent Downtime (Heroku only)
Part of the deal with Heroku's free tier is that you're allocated 550 hours/month (meaning it can't stay active 24/7), and the app is temporarily shut down after 30 minutes of inactivity. Once it becomes inactive, any Whoogle searches will still work, but it'll take an extra 10-15 seconds for the app to come back online before displaying the result, which can be frustrating if you're in a hurry.

A good solution for this is to set up a simple cronjob on any device at your home that is consistently powered on and connected to the internet (in my case, a PiHole worked perfectly). All the device needs to do is fetch app content on a consistent basis to keep the app alive in whatever ~17 hour window you want it on (17 hrs * 31 days = 527, meaning you'd still have 23 leftover hours each month if you searched outside of your target window).

For instance, adding `*/20 7-23 * * * curl https://<your heroku app name>.herokuapp.com > /home/<username>/whoogle-refresh` will fetch the home page of the app every 20 minutes between 7am and midnight, allowing for downtime from midnight to 7am. And again, this wouldn't be a hard limit - you'd still have plenty of remaining hours of uptime each month in case you were searching after this window has closed.

Since the instance is destroyed and rebuilt after inactivity, config settings will be reset once the app enters downtime. If you have configuration settings active that you'd like to keep between periods of downtime (like dark mode for example), you could instead add `*/20 7-23 * * * curl -d "dark=1" -X POST https://<your heroku app name>.herokuapp.com/config > /home/<username>/whoogle-refresh` to keep these settings more or less permanent, and still keep the app from entering downtime when you're using it.

### HTTPS Enforcement
Only needed if your setup requires Flask to redirect to HTTPS on its own -- generally this is something that doesn't need to be handled by Whoogle Search.

Note: You should have your own domain name and [an https certificate](https://letsencrypt.org/getting-started/) in order for this to work properly.

- Heroku: Ensure that the `Root URL` configuration on the home page begins with `https://` and not `http://`
- Docker build: Add `--build-arg use_https=1` to your run command
- Docker image: Set the environment variable HTTPS_ONLY=1
- Pip/Pipx: Add the `--https-only` flag to the end of the `whoogle-search-kdev` command
- Default `run` script: Modify the script locally to include the `--https-only` flag at the end of the python run command

### Using with Firefox Containers
Unfortunately, Firefox Containers do not currently pass through `POST` requests (the default) to the engine, and Firefox caches the opensearch template on initial page load. To get around this, you can take the following steps to get it working as expected:

1. Remove any existing Whoogle search engines from Firefox settings
2. Enable `GET Requests Only` in Whoogle config
3. Clear Firefox cache
4. Restart Firefox
5. Navigate to Whoogle instance and [re-add the engine](#set-whoogle-as-your-primary-search-engine)

### Reverse Proxying

#### Nginx

Here is a sample Nginx config for Whoogle:

```
server {
	server_name your_domain_name.com;
	access_log /dev/null;
	error_log /dev/null;

	location / {
	    proxy_set_header X-Real-IP $remote_addr;
	    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	    proxy_set_header X-Forwarded-Proto $scheme;
	    proxy_set_header Host $host;
	    proxy_set_header X-NginX-Proxy true;
	    proxy_pass http://localhost:5000;
	}
}
```

You can then add SSL support using LetsEncrypt by following a guide such as [this one](https://www.nginx.com/blog/using-free-ssltls-certificates-from-lets-encrypt-with-nginx/).

## Contributing

Under the hood, Whoogle is a basic Flask app with the following structure:

- `app/`
  - `routes.py`: Primary app entrypoint, contains all API routes
  - `request.py`: Handles all outbound requests, including proxied/Tor connectivity
  - `filter.py`: Functions and utilities used for filtering out content from upstream Google search results
  - `utils/`
    - `bangs.py`: All logic related to handling DDG-style "bang" queries
    - `results.py`: Utility functions for interpreting/modifying individual search results
    - `search.py`: Creates and handles new search queries
    - `session.py`: Miscellaneous methods related to user sessions
  - `templates/`
    - `index.html`: The home page template
    - `display.html`: The search results template
    - `header.html`: A general "top of the page" query header for desktop and mobile
    - `search.html`: An iframe-able search page
    - `logo.html`: A template consisting mostly of the Whoogle logo as an SVG (separated to help keep `index.html` a bit cleaner)
    - `opensearch.xml`: A template used for supporting [OpenSearch](https://developer.mozilla.org/en-US/docs/Web/OpenSearch).
    - `imageresults.html`: An "experimental" template used for supporting the "Full Size" image feature on desktop.
  - `static/<css|js>`
    - CSS/Javascript files, should be self-explanatory
  - `static/settings`
    - Key-value JSON files for establishing valid configuration values


If you're new to the project, the easiest way to get started would be to try fixing [an open bug report](https://github.com/koval01/whoogle-search-kdev/issues?q=is%3Aissue+is%3Aopen+label%3Abug). If there aren't any open, or if the open ones are too stale, try taking on a [feature request](https://github.com/koval01/whoogle-search-kdev/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement). Generally speaking, if you can write something that has any potential of breaking down in the future, you should write a test for it.

The project follows the [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/), but is liable to change. Static typing should always be used when possible. Function documentation is greatly appreciated, and typically follows the below format:

```python
def contains(x: list, y: int) -> bool:
    """Check a list (x) for the presence of an element (y)

    Args:
        x: The list to inspect
        y: The int to look for

    Returns:
        bool: True if the list contains the item, otherwise False
    """

    return y in x
```

#### Translating

Whoogle currently supports translations using [`translations.json`](https://github.com/koval01/whoogle-search-kdev/blob/main/app/static/settings/translations.json). Language values in this file need to match the "value" of the according language in [`languages.json`](https://github.com/koval01/whoogle-search-kdev/blob/main/app/static/settings/languages.json) (i.e. "lang_en" for English, "lang_es" for Spanish, etc). After you add a new set of translations to `translations.json`, open a PR with your changes and they will be merged in as soon as possible.

## FAQ
**What's the difference between this and [Searx](https://github.com/asciimoo/searx)?**

Whoogle is intended to only ever be deployed to private instances by individuals of any background, with as little effort as possible. Prior knowledge of/experience with the command line or deploying applications is not necessary to deploy Whoogle, which isn't the case with Searx. As a result, Whoogle is missing some features of Searx in order to be as easy to deploy as possible.

Whoogle also only uses Google search results, not Bing/Quant/etc, and uses the existing Google search UI to make the transition away from Google search as unnoticeable as possible.

I'm a huge fan of Searx though and encourage anyone to use that instead if they want access to other search engines/a different UI/more configuration.

**Why does the image results page look different?**

A lot of the app currently piggybacks on Google's existing support for fetching results pages with Javascript disabled. To their credit, they've done an excellent job with styling pages, but it seems that the image results page - particularly on mobile - is a little rough. Moving forward, with enough interest, I'd like to transition to fetching the results and parsing them into a unique Whoogle-fied interface that I can style myself.

## Screenshots
#### Desktop
![Whoogle Desktop](https://raw.githubusercontent.com/koval01/whoogle-search-kdev/main/docs/screenshot_desktop.png)

#### Mobile
![Whoogle Mobile](https://raw.githubusercontent.com/koval01/whoogle-search-kdev/main/docs/screenshot_mobile.png)
