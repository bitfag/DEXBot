Meaningful differences from original [DEXBot](https://github.com/Codaone/DEXBot)
--------------------------------------------------------------------------------

* Recommended installation way via `pipenv`
* Flexible Orders strategy
* Fixes to Staggered Orders strategy
* Fresh bitshares libraries used (RPC error messages are shown in details)

Installation using pipenv
-------------------------

1. Make sure you have installed required packages: `apt-get install gcc make libssl-dev`
2. [Install pipenv](https://docs.pipenv.org/) according to your system. For ubuntu 18.04:

```
# Install pip and pipenv
sudo apt install python3-pip python3-dev
pip3 install --user pipenv

# Add pipenv (and other python scripts) to PATH (if not already)
echo "PATH=$HOME/.local/bin:$PATH" >> ~/.bashrc
source ~/.bashrc
```

3. Run `pipenv install` to install the dependencies


Running
-------

```
pipenv shell
./cli.py --help
```

Documentation
-------------

Currently you can read original DEXBot wiki here <https://github.com/Codaone/DEXBot/wiki>
And original DEXBot project documentation here <https://dexbot.readthedocs.io/en/latest/>

Running in docker
-----------------


By default, local data is stored inside docker volumes. To avoid loosing configs and data, it's advised to mount custom
directories inside the container as shown below.

```
mkdir dexbot-data dexbot-config
docker run -it --rm -v `pwd`/dexbot-data:/home/dexbot/.local/share vvk123/dexbot:latest uptick addkey
docker run -it --rm -v `pwd`/dexbot-config:/home/dexbot/.config/dexbot -v `pwd`/dexbot-data:/home/dexbot/.local/share vvk123/dexbot:latest ./cli.py configure
```

To run in unattended mode you need to provide wallet passphrase:

```
docker run -d --name dexbot -e UNLOCK=pass -v `pwd`/dexbot-config:/home/dexbot/.config/dexbot -v `pwd`/dexbot-data:/home/dexbot/.local/share vvk123/dexbot:latest ./cli.py run
```

Assuming you have created a Docker secret named "passphrase" in your swarm, you can also get it from there:

```
printf <pass> | docker secret create passphrase -
docker run -d --name dexbot -e UNLOCK=/run/secrets/passphrase -v `pwd`/dexbot-config:/home/dexbot/.config/dexbot -v `pwd`/dexbot-data:/home/dexbot/.local/share vvk123/dexbot:latest ./cli.py run
```

Getting help
------------

Feel free to open an issue.

When reporting bugs related to strategy behavior, make sure you're attaching dexbot.log and config.yml files.

Contributing
------------

Install dev packages: `pipenv install --dev`

Activate pre-commit hooks: `pre-commit install`

Direct your PRs to `devel` branch.
