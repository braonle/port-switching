from flask import Flask, render_template, request, redirect, url_for, g, flash
from database import DBHandler
import re
import paramiko
import threading
from configparser import ConfigParser
import queue
import logging


# DEB: /etc/default/iptables
# RPM: /etc/sysconfig/iptables

app = Flask(__name__)
app.config.from_pyfile('flask.conf')
regexpip = "^(((25[1-5])|(2[1-4][0-9])|([0-1]?[0-9]{1,2}))\.){3,3}\
((25[1-5])|(2[1-4][0-9])|([0-1]?[0-9]{1,2}))$"
parser = ConfigParser()


def log(s):
    parser.read(filenames='settings.conf')
    lg = parser.get(section="COMMON", option="logfile")
    logging.basicConfig(filename=lg, level=logging.DEBUG)
    flash(s)
    logging.debug(s)


def log_tuple(q):
    parser.read(filenames='settings.conf')
    lg = parser.get(section="COMMON", option="logfile")
    logging.basicConfig(filename=lg, level=logging.DEBUG)
    for s in q:
        flash(s)
        logging.debug(s)


@app.before_request
def prepare():
    g.database = DBHandler("settings.conf")


@app.teardown_request
def clean(exc):
    db = getattr(g, 'database', None)
    if db is not None:
        db.__del__()


@app.route('/')
def main():
    rt = ({'name': row[0], 'ext_ip': row[1]} for row in g.database.get_routers())
    sw = ({'ext_p': rows[0], 'ip': rows[1], 'int_p': rows[2]}
          for rows in g.database.get_switchings())
    return render_template('main.html', routers=rt, switching=sw)


@app.route('/get/routers/edit/<string:name>', methods=['GET'])
def redirect_edit_router(name):
    res = g.database.get_router(name)
    return render_template('edit_router.html', name=res[0], ip=res[1])


@app.route('/get/switching/edit/<int:port>', methods=['GET'])
def redirect_edit_switching(port):
    res = g.database.get_switching(port)
    return render_template('edit_switching.html', ext_p=res[0], ip=res[1], int_p=res[2])


@app.route('/post/routers/edit/<string:name>', methods=['POST'])
def edit_router(name):
    new_name = request.form.get('name', None)
    ip = request.form.get('ip', None)
    if name is None or ip is None:
        log('Smth bad has happened')
        return redirect(url_for('redirect_edit_router', name=name))
    elif len(new_name) == 0:
        log("Empty name")
        return redirect(url_for('redirect_edit_router', name=name))
    elif re.match(regexpip, ip) is None:
        log("Bad IP address")
        return redirect(url_for('redirect_edit_router', name=name))
    else:
        log(g.database.edit_router(name, ip, new_name))
        return redirect(url_for('main'))


@app.route('/post/switching/edit/<int:port>', methods=['POST'])
def edit_switching(port):
    new_ep = request.form.get('ext_p', None)
    ip = request.form.get('ip', None)
    new_p = request.form.get('int_p', None)
    if new_ep is None or ip is None or new_p is None:
        log('Smth bad has happened')
        return redirect(url_for('redirect_edit_switching', port=port))
    elif new_ep.isdigit() is False:
        log("Bad external port")
        return redirect(url_for('redirect_edit_switching', port=port))
    elif new_p.isdigit() is False:
        log("Bad internal port")
        return redirect(url_for('redirect_edit_switching', port=port))
    elif re.match(regexpip, ip) is None:
        log("Bad IP address")
        return redirect(url_for('redirect_edit_switching', port=port))
    else:
        flash(g.database.edit_switching(port, new_ep, ip, new_p))
        return redirect(url_for('main'))


@app.route('/get/routers/add', methods=['GET'])
def add_router_red():
    return render_template('add_router.html')


@app.route('/get/switching/add', methods=['GET'])
def add_switching_red():
    return render_template('add_switching.html')


@app.route('/post/routers/add', methods=['POST'])
def add_router():
    name = request.form.get('name', None)
    ip = request.form.get('ip', None)
    if name is None or ip is None:
        log('Smth bad has happened')
    elif len(name) == 0:
        log('No name supplied')
    elif re.match(regexpip, ip) is None:
        log("Bad IP address")
    else:
        log(g.database.add_router(name, ip))
    return redirect(url_for('main'))


@app.route('/post/switching/add', methods=['POST'])
def add_switching():
    ext_p = request.form.get('ext_p', None)
    ip = request.form.get('ip', None)
    int_p = request.form.get('int_p', None)
    if ext_p is None or ip is None or int_p is None:
        log('Smth bad has happened')
    elif ext_p.isdigit() is False:
        log("Bad external port")
    elif int_p.isdigit() is False:
        log("Bad internal port")
    elif re.match(regexpip, ip) is None:
        log("Bad IP address")
    else:
        log(g.database.add_switching(ext_p, ip, int_p))
    return redirect(url_for('main'))


def ssh_single(ip):
    parser.read(filenames='settings.conf')
    path = parser.get(section="SSH", option="path")
    outif = parser.get(section="SSH", option="output_if")
    inif = parser.get(section="SSH", option="input_if")
    ssh_port = parser.getint(section="SSH", option="port")
    login = parser.get(section="SSH", option="login")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.RSAKey.from_private_key_file(parser.get(section="SSH", option="keyfile"))
    client.connect(hostname=ip, username=login, pkey=key, port=ssh_port, timeout=30)
    fclient = client.open_sftp()
    file = fclient.open(path, "w")
    res = [{'ep': line[0], 'ip': line[1], 'p': line[2]} for line in g.database.get_switchings()]
    file.writelines(render_template('iptables_template', param=res, outif=outif, inif=inif, eip=ip))
    file.flush()
    file.close()
    fclient.close()
    client.exec_command('iptables-restore < {path}'.format(path=path))
    client.close()


@app.route('/get/ssh/send/<string:router>', methods=["GET"])
def ssh_send(router):
    try:
        rt, ip = g.database.get_router(router)
        ssh_single(ip)
        log("Successful sending for {name}".format(name=router))
    except OSError as err:
        log(err.__str__() + " for {name}".format(name=router))
    except paramiko.AuthenticationException as err:
        log(err.__str__() + " for {name}".format(name=router))
    return redirect(url_for('main'))


@app.route('/get/ssh/send_all', methods=["GET"])
def ssh_send_all():
    res = g.database.get_routers()
    for src in res:
        try:
            ssh_single(src[1])
            log("Successful sending for {name}".format(name=src[0]))
        except OSError as err:
            log(err.__str__() + " for {name}".format(name=src[0]))
        except paramiko.AuthenticationException as err:
            log(err.__str__() + " for {name}".format(name=src[0]))
    return redirect(url_for('main'))


@app.route('/get/router/delete/<string:router>', methods=['GET'])
def delete_router(router):
    log(g.database.delete_router(router))
    return redirect(url_for('main'))


@app.route('/get/switching/delete/<string:port>', methods=['GET'])
def delete_switching(port):
    log(g.database.delete_switching(port))
    return redirect(url_for('main'))


app.run(host='0.0.0.0')
