# JADS-cloudflare-ddns

Just Another cloudflare DDNS Script to periodically check your public IP address and update one or more DNS records accordingly.

Not everyone wants to use Docker for their DDNS scripts, despite it seeming to be the way a lot of the modern ones are going. This one doesn't require Docker (in fact, at present I don't have a Docker image built for this), but still supports updating multiple domains and multiple records within each domain.

You do not need to open or forward any ports on your router for this to work, as all connections are initiated from whatever host `ddns.py` is running on.

## [Requirements](#requirements)

* Cloudflare API token
  * You need to generate an API token for the Cloudflare account managing the DNS records. See https://dash.cloudflare.com/profile/api-tokens to create one.
  * Make sure you grant the token "Edit DNS" access, otherwise it won't work
* Cloudflare zone ID
  * See the [Cloudflare docs](https://developers.cloudflare.com/fundamentals/get-started/basic-tasks/find-account-and-zone-ids/) for details on how to find your zone ID
* Cloudflare record ID
  * See the [Cloudflare API docs](https://api.cloudflare.com/#dns-records-for-a-zone-list-dns-records) for details on how to get the record IDs for your record(s)


## [Get started](#get-started)

First, clone this repository.

Then, get started by copying `example-config.yaml` to `domains.yaml`:

```bash
cd jads-cloudflare-ddns/
cp example-config.yaml domains.yaml
```

Then, edit the file with your editor of choice (e.g. `vim` or `nano`), and replace the default values for the `auth_key` and your domains (including `zone_id` and records).

Finally, run the script -- I suggest using `-v` at least for the first time to make sure there are no errors.

```bash
./ddns.py -c ./domains.yaml -v
```

**Note:** I strongly suggest not using `-v` if you're running the script via an automated scheduler, as it will reveal sensitive information like your Cloudflare API key.

### [Automate!](#automate)

If you want to have this run automatically, I suggest creating a directory to store the configuration file in, like `/etc/ddns`:

```bash
sudo mkdir /etc/ddns
```

Then copy the configuration file you just made into there:

```bash
sudo cp ./domains.yaml /etc/ddns/
```

Move the script to somewhere logical, like `/usr/local/bin`:

```bash
sudo cp ./ddns.py /usr/local/bin/
```

Alternatively, you could create a symlink so getting updates is as simple as running `git pull origin main`:

```bash
sudo ln -s /usr/local/bin/ddns.py $(pwd)/ddns.py
```

Finally, create a cron job to run the script periodically -- in this example, I have it set to run every 5 minutes:

```bash
sudo echo "*/5 * * * * root /usr/local/bin/ddns.py" >> /etc/crontab
```

Voila! You now have DDNS.

**Note:** I do not recommend running this as the `root` user; the above examples are for demonstration purposes only, and I highly recommend setting up a non-privileged user to run the script instead

## [Prometheus monitoring](#prometheus-monitoring)

JADS-cloudflare-ddns also generates output that Prometheus can scrape using the [textfile collector](https://github.com/prometheus/node_exporter#textfile-collector) built in to the node_exporter module -- simply pipe the output of `ddns.py` to a `sponge`, like this:

```bash
./ddns.py | sponge /tmp/ddns_stats.prom
```

If you've scheduled the script to run with `cron`, just tack it on the end of the cron job, like so:

```
*/5 * * * * root /usr/local/bin/ddns.py | sponge /tmp/ddns_stats.prom
```

And then update your node_exporter service configuration accordingly, by adding `--collector.textfile.directory=/tmp` to the `ExecStart` command

## [Configuration](#configuration)

Domain and authentication configuration is done using a YAML file. By default, the script will look for `domains.yaml` in the `/etc/ddns` directory, but you can choose a custom config file location using the `-c` option when calling the script:

```bash
./ddns.py -c /custom/config/file/path.yaml
```

For debugging purposes, you can use the verbose option; `-v`, which will print details of what the script is doing to `stderr` (`stderr` is used to prevent the use of the `-v` flag from interfering with the output generated for Prometheus).

### [Example configuration file](#example-configuration-file)

```yaml
---
# API key for your Cloudflare account
# Required: yes
auth_key: "auth_key_goes_here"

# Path to a file to store the current public IP address in
# Default: "/etc/ddns/cache.txt"
# Required: no
cache_file: "/etc/ddns/cache.txt" 

# The list of domains to be managed
domains:
    # The name of the domain. Can be anything you want, it's just an identifier to make managing the configuration easier
    # Required: yes
  - name: "example.com"
    # The zone ID for the domain being managed
    # Required: yes
    zone_id: "zone_id_goes_here"
    records:
        # The name of the record that will point to the public IP address
        # Required: yes
      - name: "example.com"
        # The ID of the record
        # Required: yes
        record_id: "record_id_goes_here"
```

# [License](#license)

This project is licensed under GNU GPLv3. See [LICENSE.md](./LICENSE) for more details.

# [Contributing](#contributing)

If you would like to contribute directly to this project, please feel free to [create a pull request](https://github.com/llamalump/JADS-cloudflare-ddns/compare).

If you're not comfortable writing the code yourself, or just want to ask a question or raise an issue, please [create an issue](https://github.com/llamalump/JADS-cloudflare-ddns/issues/new/choose), providing as much detail as possible.

# [Future Improvements](#future-improvements)

* Use [Cloudflare's cdn-cgi/trace](https://www.cloudflare.com/cdn-cgi/trace) to improve privacy
* Be smarter about modifying DNS records
* IPv6 (AAAA records) support
* Refactor to allow using different accounts for each domain
* Make the output more configurable (not everyone wants to see output that suits Prometheus)
  * Also, `sponge` is not necessarily available on all distros like it is on Ubuntu (where this script was developed) -- I need to make this more accessible for other platforms
* Write an install script to streamline the deployment process
