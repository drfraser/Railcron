"""
Miscellaneous functions
"""
from datetime import datetime, timedelta
import yaml

from prefect import flow, get_run_logger
from prefect_email import EmailServerCredentials, email_send_message, SMTPType
from prefect_shell import shell_run_command

### loc of cfg file
def create_flows(flow_generator, filters, config_file="./odfetch.yaml"):
    """Dynamically create flows using calling module's flow generator function

       Args:
           flow_generator: Generator function that creates flows
           filters: List of prefixes to search for in config file that define flows' parameters
           config_file: File of flow configuration parameters

       Returns: dict of new Prefect flow functions
                globals() also updated with new functions
    """
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
        for k in config_data['settings'].keys():
            config_data[root][k] = config_data['settings'][k]
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
    if cfg.MAIL_FROM in (None, "") or cfg.MAIL_TO in (None, ""):
        return ""
    if cfg.MAIL_SRV in (None, "", "sendmail"):
        parts = [[cfg.MAIL_CC, "-c ", ""],
                 [cfg.MAIL_BCC, "-b ", ""],
                 [cfg.MAIL_FROM, "-r ", ""]]
        for mailcc in parts:
            if mailcc[0]: mailcc[2] = mailcc[1] + mailcc[0]
        cmd = f"echo \"{msg}\" | mail {parts[2][2]} -s \"{subject}\" {parts[0][2]} {parts[1][2]} \"{cfg.MAIL_TO}\" "
        output = shell_run_command(command=cmd, return_all=True)
    else:
        email_server_credentials = EmailServerCredentials(
            username=cfg.MAIL_LOGIN.strip(),
            password=cfg.MAIL_PWD.strip(),
            smtp_server=cfg.MAIL_SRV.strip(),
            smtp_type=getattr(SMTPType, cfg.MAIL_TYPE.strip()),
            smtp_port=cfg.MAIL_PORT,
        )
        try:
            subject = email_send_message(
                subject=subject,
                msg=msg,
                email_server_credentials=email_server_credentials,
                email_to=cfg.MAIL_TO.strip(),
                email_to_cc=(cfg.MAIL_CC.strip() if cfg.MAIL_CC else None),
                email_to_bcc=(cfg.MAIL_BCC.strip() if cfg.MAIL_BCC else None),
            )
        except Exception as exc:
            logger = get_run_logger()
            logger.error("Failure to email message")
            logger.error(exc)
        output = subject
    return output
