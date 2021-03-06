#!/usr/bin/env python3
import logging
import os
import os.path
import signal
import sys
import time
from multiprocessing import freeze_support

import click  # noqa: E402
from dexbot.cli_conf import SYSTEMD_SERVICE_NAME, get_whiptail, setup_systemd
from dexbot.config import DEFAULT_CONFIG_FILE, Config
from dexbot.helper import initialize_data_folders, initialize_orders_log
from dexbot.storage import Storage
from dexbot.ui import chain, configfile, unlock, verbose

from . import errors, helper
from .cli_conf import configure_dexbot, dexbot_service_running
from .worker import WorkerInfrastructure

# We need to do this before importing click
if "LANG" not in os.environ:
    os.environ['LANG'] = 'C.UTF-8'


log = logging.getLogger(__name__)

# Initial logging before proper setup.
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Configure orders logging
initialize_orders_log()

# Initialize data folders
initialize_data_folders()


@click.group()
@click.option("--configfile", default=DEFAULT_CONFIG_FILE)
@click.option(
    '--logfile',
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help='Override logfile location (example: ~/dexbot.log)',
)
@click.option('--verbose', '-v', type=int, default=3, help='Verbosity (0-15)')
@click.option('--systemd/--no-systemd', '-d', default=False, help='Run as a daemon from systemd')
@click.option('--pidfile', '-p', type=click.Path(dir_okay=False, writable=True), default='', help='File to write PID')
@click.option('--sortnodes', '-s', type=int, default=-1, help='Sort nodes, w/max timeout in sec. [sec > 0]')
@click.pass_context
def main(ctx, **kwargs):
    ctx.obj = {}
    for k, v in kwargs.items():
        ctx.obj[k] = v


@main.command()
@click.pass_context
@configfile
@chain
@unlock
@verbose
def run(ctx):
    """ Continuously run the worker
    """
    if ctx.obj['pidfile']:
        with open(ctx.obj['pidfile'], 'w') as fd:
            fd.write(str(os.getpid()))
    try:
        worker = WorkerInfrastructure(ctx.config)
        # Set up signalling. do it here as of no relevance to GUI
        kill_workers = worker_job(worker, lambda: worker.stop(pause=True))
        # These first two UNIX & Windows
        signal.signal(signal.SIGTERM, kill_workers)
        signal.signal(signal.SIGINT, kill_workers)
        try:
            # These signals are UNIX-only territory, will ValueError or AttributeError here on Windows (depending on
            # python version)
            signal.signal(signal.SIGHUP, kill_workers)
            # TODO: reload config on SIGUSR1
            # signal.signal(signal.SIGUSR1, lambda x, y: worker.do_next_tick(worker.reread_config))
        except (ValueError, AttributeError):
            log.debug("Cannot set all signals -- not available on this platform")
        if ctx.obj['systemd']:
            try:
                import sdnotify  # A soft dependency on sdnotify -- don't crash on non-systemd systems

                n = sdnotify.SystemdNotifier()
                n.notify("READY=1")
            except BaseException:
                log.debug("sdnotify not available")
        worker.run()
    except errors.NoWorkersAvailable:
        sys.exit(70)  # 70= "Software error" in /usr/include/sysexts.h
    finally:
        if ctx.obj['pidfile']:
            helper.remove(ctx.obj['pidfile'])


@main.command()
@click.pass_context
@configfile
@chain
@unlock
def runservice():
    """ Continuously run the worker as a service
    """
    if dexbot_service_running():
        click.echo("Stopping dexbot daemon")
        os.system('systemctl --user stop dexbot')

    if not os.path.exists(SYSTEMD_SERVICE_NAME):
        setup_systemd(get_whiptail('DEXBot configure'), {})

    click.echo("Starting dexbot daemon")
    os.system("systemctl --user start dexbot")


@main.command()
@click.pass_context
@configfile
@chain
@unlock
def configure(ctx):
    """ Interactively configure dexbot
    """
    # Make sure the dexbot service isn't running while we do the config edits
    if dexbot_service_running():
        click.echo("Stopping dexbot daemon")
        os.system('systemctl --user stop dexbot')

    config = Config(path=ctx.obj['configfile'])
    configure_dexbot(config, ctx)
    config.save_config()

    click.echo("New configuration saved")
    if config.get('systemd_status', 'disabled') == 'enabled':
        click.echo("Starting dexbot daemon")
        os.system("systemctl --user start dexbot")


@main.command()
@click.argument('worker_name')
def drop_state(worker_name):
    """ Drop state of the worker (sqlite data)
    """
    click.echo('Dropping state for {}'.format(worker_name))
    Storage.clear_worker_data(worker_name)
    time.sleep(1)


def worker_job(worker, job):
    return lambda x, y: worker.do_next_tick(job)


if __name__ == '__main__':
    """ Add freeze_support for when a program which uses multiprocessing (node_manager) has been
        frozen to produce a Windows executable. If the freeze_support() line is omitted
        then trying to run the frozen executable will raise RuntimeError. Calling
        freeze_support() has no effect when invoked on any operating system other than Windows.
    """
    freeze_support()
    main()
