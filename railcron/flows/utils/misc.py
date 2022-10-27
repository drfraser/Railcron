"""
Miscellaneous functions
"""
from datetime import datetime, timedelta
import os
import yaml

from prefect import flow, get_run_logger
from prefect_email import EmailServerCredentials, email_send_message, SMTPType
from prefect_shell import shell_run_command

### loc of cfg file
def create_flows(flow_generator, filters):
    """Dynamically create flows using calling module's flow generator function

       Args:
           flow_generator: Generator function that creates flows
           filters: List of prefixes to search for in blocks/config file that define flows' parameters

       Returns: dict of new Prefect flow functions
                globals() also updated with new functions
    """
    # read list of known blocks (names) and/or config file
    config_file = os.getenv('RAILCRON_CFG', '.') + "/railcron.yml"
    with open(config_file, mode="rb") as file:
        config_data = yaml.safe_load(file)
    prefect_flows = {}
    flow_names = [x for prefix in filters for x in config_data.keys() if x.startswith(prefix)]
    for fname in flow_names:
        prefect_flows[fname] = flow_generator(fname)
        globals()[fname] = prefect_flows[fname]
    return prefect_flows


def load_config(config_file, root):
    """Reads YAML file of config settings such as username/password"""
    with open(config_file, mode="rb") as file:
        config_data = yaml.safe_load(file)
        config_data[root]['settings'] = {}
        for k in config_data['settings'].keys():
            config_data[root]['settings'][k] = config_data['settings'][k]
        for sec in ['nrdatafeeds', 'opendata']:
            for key in ['username', 'password']:
                if key in config_data[root].keys():
                    if sec in config_data[root][key]:
                        config_data[root][key] = config_data[root][key].replace(
                            f"{sec}__{key}", config_data[sec][key])
        return config_data[root]


def get_day_of_week(yesterday=False, lowercase=True):
    """Returns the name of the day of the week"""
    the_date = datetime.today()
    if yesterday:
        the_date = the_date + timedelta(days=-1)
    theday = the_date.strftime('%a')
    return (theday if not lowercase else theday.lower())


def get_current_ymd(yesterday=False, strip_zeros=False):
    """Returns list of numerical parts of date"""
    the_date = datetime.today()
    if yesterday:
        the_date = the_date + timedelta(days=-1)
    cyear = the_date.strftime('%Y')
    cmon = the_date.strftime('%m')
    cday = the_date.strftime('%d')
    if strip_zeros:
        cmon = cmon.lstrip('0')
        cday = cday.lstrip('0')
    return [cyear, cmon, cday]


@flow
def email_message(cfg, subject, msg):
    """Flow to send an email through localhost or specified mail server"""
    if cfg.settings.MAIL_FROM in (None, "") or cfg.settings.MAIL_TO in (None, ""):
        return ""
    if cfg.settings.MAIL_SRV in (None, "", "sendmail"):
        parts = [[cfg.settings.MAIL_CC, "-c ", ""],
                 [cfg.settings.MAIL_BCC, "-b ", ""],
                 [cfg.settings.MAIL_FROM, "-r ", ""]]
        for mailcc in parts:
            if mailcc[0]: mailcc[2] = mailcc[1] + mailcc[0]
        cmd = f"echo \"{msg}\" | mail {parts[2][2]} -s \"{subject}\" {parts[0][2]} {parts[1][2]} \"{cfg.settings.MAIL_TO}\" "
        output = shell_run_command(command=cmd, return_all=True)
    else:
        email_server_credentials = EmailServerCredentials(
            username=cfg.settings.MAIL_LOGIN.strip(),
            password=cfg.settings.MAIL_PWD.strip(),
            smtp_server=cfg.settings.MAIL_SRV.strip(),
            smtp_type=getattr(SMTPType, cfg.settings.MAIL_TYPE.strip()),
            smtp_port=cfg.settings.MAIL_PORT,
        )
        try:
            subject = email_send_message(
                subject=subject,
                msg=msg,
                email_server_credentials=email_server_credentials,
                email_to=cfg.settings.MAIL_TO.strip(),
                email_to_cc=(cfg.settings.MAIL_CC.strip() if cfg.settings.MAIL_CC else None),
                email_to_bcc=(cfg.settings.MAIL_BCC.strip() if cfg.settings.MAIL_BCC else None),
            )
        except Exception as exc:
            logger = get_run_logger()
            logger.error("Failure to email message")
            logger.error(exc)
        output = subject
    return output
