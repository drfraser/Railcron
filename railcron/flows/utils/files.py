"""
Various functions to assist with manipulating and archiving files.
LocalFileSystem block not used as extra steps involved in writing files.

TODO: Use RemoteFileSystem to support SSH based backup instead of rsync?
      Or for archiving original copies to any remote file system?
"""
import hashlib
import os
import pathlib
from shutil import rmtree
from tempfile import mkdtemp

from prefect_shell import shell_run_command

from .misc import get_current_ymd


compressions = {'xz': ('xz -9 -T2', '.xz'),
                'zstd': ('zstd -q --rm -T2 -19', '.zst'),
                'gzip': ('gzip -9', '.gz'),
                'bzip2': ('bzip2 -9', '.bz2'),
                '.gz': 'gunzip',
                '.tbz2': 'bunzip2',
                '.bz2': 'bunzip2',
                '.xz': 'xz -d',
                '.zst': 'zstd'
}

async def async_recompress(cfg, filepath):
    """Recompresses the specified file to desired format (async version)

       Can't use @sync_compatible because shell_run_command is async task and
       return value is not return value of shell_run_command

       Args:
           cfg: Block with configuration info
           filepath: Path of original file

       Returns: path to the new file
    """
    if cfg.settings.recompress not in compressions.keys():
        raise Exception("Unsupported compression scheme")
    oldext = os.path.splitext(os.path.basename(filepath))[1]
    tool = compressions[oldext]
    dirpath = os.path.dirname(filepath)
    newname = os.path.splitext(os.path.basename(filepath))[0]
    if oldext == '.tbz2': newname += ".tar"
    cmd = f"{tool} {filepath} ; {compressions[cfg.settings.recompress][0]} {newname}"
    # handle when ext of original file does not need to be stripped off
    if cfg.filetype == '--':
        cmd = f"{compressions[cfg.settings.recompress][0]} {filepath}"
        newname = filepath
    await shell_run_command(command=cmd, helper_command=f"cd {dirpath}", return_all=True)
    return os.path.join(dirpath, newname + compressions[cfg.settings.recompress][1])


def recompress(cfg, filepath):
    """Recompresses the specified file to desired format

       Args:
           cfg: Block with configuration info
           filepath: Path of original file

       Returns: path to the new file
    """
    if cfg.settings.recompress not in compressions.keys():
        raise Exception("Unsupported compression scheme")
    oldext = os.path.splitext(os.path.basename(filepath))[1]
    tool = compressions[oldext]
    dirpath = os.path.dirname(filepath)
    newname = os.path.splitext(os.path.basename(filepath))[0]
    if oldext == '.tbz2': newname += ".tar"
    cmd = f"{tool} {filepath} ; {compressions[cfg.settings.recompress][0]} {newname}"
    # handle when ext of original file does not need to be stripped off
    if cfg.filetype == '--':
        cmd = f"{compressions[cfg.settings.recompress][0]} {filepath}"
        newname = filepath
    shell_run_command(command=cmd, helper_command=f"cd {dirpath}", return_all=True)
    return os.path.join(dirpath, newname + compressions[cfg.settings.recompress][1])


def unzip_file(zipfile):
    """Unzips fullpath ZIP file to tmp directory"""
    tmpdir = mkdtemp(dir="/tmp")
    dirpath = os.path.dirname(zipfile)
    shell_run_command(
        command=f"unzip \"{zipfile}\" -d {tmpdir}",
        helper_command=f"cd \"{dirpath}\"",
        return_all=True)
    return tmpdir


def tar_and_compress(compressor, filepath, tmpdir):
    """Tar and recompresss a collection of files

       Args:
           compression: name of compression utility to use
           filepath: Path of original file
           tmpdir: Path of directory where it is stored

       Returns: name of new file
    """
    if compressor not in compressions.keys():
        raise Exception("Unsupported compression scheme")
    newname = os.path.splitext(filepath)[0]
    newname += ".tar" + compressions[compressor][1]
    # UNIX vs BSD?
    cmd = f"tar -I '{compressions[compressor][0]}' -c -f \"{newname}\" *"
    shell_run_command(command=cmd, helper_command=f"cd {tmpdir}",
                      return_all=True)
    os.unlink(filepath)
    rmtree(tmpdir)
    return newname


def archive_data_to_file(resp, filepath_prefix, filename, streaming=True):
    """Saves data from a HTTP response into a file

       Args:
           resp: HTTP response object (or its data)
           prefix: Prefix of the file's path
           filename: Name to use for the new file
           streaming: True if the HTTP response is a streaming one

       Returns: path of new file
    """
    os.makedirs(filepath_prefix, mode=0o755, exist_ok=True)
    filepath = os.path.join(filepath_prefix, filename)
    if not streaming:
        with open(filepath, 'wb') as fd:
            fd.write(resp)
    else:
        with open(filepath, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=100*1024):
                fd.write(chunk)
    return filepath


def file_changed(fname, filepath, file_hash):
    """Determines if saved hash of a file equals the hash of the lastest version

       Args:
           fname: Name of the flow
           filepath: Path to the file
           file_hash: Prefect JSON block with current hash info
                      Name of block should be "{fname}-hash"

       Returns: hash(old_file) == hash(new_file)
    """
    hash_value = hashlib.md5(pathlib.Path(filepath).read_bytes()).hexdigest()
    if hash_value != file_hash.value["last_hash"]:
        file_hash.value["last_hash"] = hash_value
        file_hash.save(name=f"{fname}-hash".replace('_','-'), overwrite=True)
        return True
    return False


def exec_rsync(cfg):
    """Executes the rsync command in the supplied cfg Block

       Templated variables in rsync command updated based on the date:
           cyear / cmon / cday:  Current date
           yyear / ymon / yday:  Yesterday

       Note: Directory first changed to that specified by 'archive_path'
    """
    output = None
    if cfg.settings.BACKUP_HOST not in (None, ""):
        cyear, cmon, cday = get_current_ymd(yesterday=False)
        yyear, ymon, yday = get_current_ymd(yesterday=True)
        cmd = cfg.rsync.replace("$BACKUP_HOST", cfg.settings.BACKUP_HOST).replace("$BACKUP_ROOT", cfg.settings.BACKUP_ROOT)
        cmd  = cmd.replace("$cyear", cyear).replace("$cmon", cmon).replace("$cday", cday)
        cmd  = cmd.replace("$yyear", yyear).replace("$ymon", ymon).replace("$yday", yday)
        output = shell_run_command(command=cmd, helper_command=f"cd {cfg.archive_path}", return_all=True)
    return output
