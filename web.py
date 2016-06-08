# -*-coding:utf-8-*-
# /usr/bin/python3
from flask import Flask, render_template, request, redirect, url_for, g, flash, abort
from database import DBHandler
import paramiko
from configparser import ConfigParser
import logging
import ipaddress


# DEB: /etc/default/iptables
# RPM: /etc/sysconfig/iptables

app = Flask(__name__)
app.config.from_pyfile('flask.conf')
parser = ConfigParser()
parser.read(filenames='settings.conf')
logging.basicConfig(
    filename=parser.get(section="COMMON", option="logfile"),
    level=logging.DEBUG,
    filemode="w",
    format='%(levelname)s:%(asctime)s - %(message)s'
)


# Made a separate procedure for easier adding new destinations
# for logging
def log(s):
    flash(s)
    logging.debug(s)
    print(s)


@app.before_request
def prepare():
    g.database = DBHandler("settings.conf")


@app.teardown_request
def clean(exc):
    db = getattr(g, 'database', None)
    if db is not None:
        del db
        g.db = None


@app.route('/')
def main():
    rt = [{'name': row[0], 'ext_ip': row[1]} for row in g.database.get_routers()]
    sw = [{'ext_p': rows[0], 'ip': rows[1], 'int_p': rows[2]}
          for rows in g.database.get_forwardings()]
    maxhost = 9
    for i in rt:
        if len(i['name']) > maxhost:
            maxhost = len(i['name'])
    return render_template('main.html', routers=rt, forwarding=sw, hsize=maxhost,
                           title='Main page')


@app.route('/get/routers/edit')
def redirect_edit_router(**kwargs):
    if len(kwargs) == 0:
        name = request.args.get('name')
        res = g.database.get_router(name)
        if res is None:
            return abort(404)
        res = (res[0], res[1], name)
    else:
        res = kwargs['res']
    return render_template('edit_router.html', name=res[0], ip=res[1], new_name=res[2],
                           title='Edit {name}'.format(name=res[0]))


@app.route('/get/forwarding/edit')
def redirect_edit_forwarding(**kwargs):
    if len(kwargs) == 0:
        port = request.args.get('port')
        res = g.database.get_forwarding(port)
        if res is None:
            return abort(404)
        res = (res[0], res[1], res[2], port)
    else:
        res = kwargs['res']
    return render_template('edit_forwarding.html', ext_p=res[0], ip=res[1], int_p=res[2], port=res[3],
                           title='Edit {name}'.format(name=res[0]))


@app.route('/post/routers/edit/<string:name>', methods=['POST'])
def edit_router(name):
    res = [name, request.form.get('ip'), request.form.get('new_name')]
    flg = False
    try:
        net = ipaddress.ip_address(res[1])
    except ValueError:
        net = None
    if name is None or res[1] is None or res[0] is None:
        log('Smth bad has happened')
        flg = True
    if len(res[2]) == 0:
        log("Empty name")
        flg = True
    if net is None:
        log("Bad IP address")
        flg = True

    if flg:
        return redirect_edit_router(res=res)
    else:
        r = g.database.edit_router(name, res[1], res[2])
        log(r[1])
        if r[0]:
            return redirect_edit_router(res=res)
    return redirect(url_for('main'))


@app.route('/post/forwarding/edit/<int:port>', methods=['POST'])
def edit_forwarding(port):
    res = [request.form.get('ext_p'), request.form.get('ip'),
           request.form.get('int_p'), port]
    flg = False
    try:
        net = ipaddress.ip_address(res[1])
    except ValueError:
        net = None
    if res[0] is None or res[1] is None or res[2] is None:
        log('Smth bad has happened')
        flg = True
    if not res[0].isdigit() or not 1 <= int(res[0]) <= 65535:
        log("Bad external port")
        flg = True
    if not res[2].isdigit() or not 1 <= int(res[2]) <= 65535:
        log("Bad internal port")
        flg = True
    if net is None:
        log("Bad IP address")
        flg = True
    if flg:
        return redirect_edit_forwarding(res=res)
    else:
        r = g.database.edit_forwarding(port, res[0], res[1], res[2])
        log(r[1])
        if r[0]:
            return redirect_edit_forwarding(res=res)
    return redirect(url_for('main'))


@app.route('/get/routers/add')
def add_router_red(**kwargs):
    param = kwargs.get('param')
    if param is None:
        param = ['', '']
    for i in range(0, 1):
        if param[i] is None:
            param[i] = ''
    return render_template('add_router.html', name=param[0], add=param[1],
                           title='Add router')


@app.route('/get/forwarding/add')
def add_forwarding_red(**kwargs):
    param = kwargs.get('param')
    if param is None:
        param = ['', '', '']
    for i in range(0, 2):
        if param[i] is None:
            param[i] = ''
    return render_template('add_forwarding.html', ep=param[0], ip=param[1], p=param[2],
                           title='Add forwarding')


@app.route('/post/routers/add', methods=['POST'])
def add_router():
    pr = [request.form.get('name'), request.form.get('ip')]
    flg = False
    try:
        net = ipaddress.ip_address(pr[1])
    except ValueError:
        net = None
    if pr[0] is None or pr[1] is None:
        log('Smth bad has happened')
    if len(pr[0]) == 0:
        log('No name supplied')
        flg = True
    if net is None:
        log("Bad IP address")
        flg = True
    if flg:
        return add_router_red(param=pr)
    else:
        res = g.database.add_router(pr[0], pr[1])
        log(res[1])
        if res[0]:
            return add_router_red(param=pr)
    return redirect(url_for('main'))


@app.route('/post/forwarding/add', methods=['POST'])
def add_forwarding():
    pr = [request.form.get('ext_p'), request.form.get('ip'),
          request.form.get('int_p')]
    flg = False
    try:
        net = ipaddress.ip_address(pr[1])
    except ValueError:
        net = None
    if pr[0] is None or pr[1] is None or pr[2] is None:
        log('Smth bad has happened')
    if not pr[0].isdigit() or not 1 <= int(pr[0]) <= 65535:
        log("Bad external port")
        flg = True
    if net is None:
        log("Bad IP address")
        flg = True
    if not pr[2].isdigit() or not 1 <= int(pr[2]) <= 65535:
        log("Bad internal port")
        flg = True
    if flg:
        return add_forwarding_red(param=pr)
    else:
        res = g.database.add_forwarding(pr[0], pr[1], pr[2])
        log(res[1])
        if res[0]:
            return add_forwarding_red(param=pr)
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
    res = [{'ext_p': line[0], 'ip': line[1], 'p': line[2]} for line in g.database.get_forwardings()]
    file.writelines(render_template('iptables_template',
                                    param=res, out_if=outif, in_if=inif, ext_ip=ip))
    file.flush()
    file.close()
    fclient.close()
    client.exec_command('iptables-restore < {path}'.format(path=path))
    client.close()


@app.route('/get/ssh/send/<string:router>')
def ssh_send(router):
    try:
        rt, ip = g.database.get_router(router)
        ssh_single(ip)
        log("Successful sending for {name}".format(name=router))
    except OSError as err:
        log(str(err) + " for {name}".format(name=router))
    except paramiko.AuthenticationException as err:
        log(str(err) + " for {name}".format(name=router))
    return redirect(url_for('main'))


@app.route('/get/ssh/send_all')
def ssh_send_all():
    res = g.database.get_routers()
    for src in res:
        try:
            ssh_single(src[1])
            log("Successful sending for {name}".format(name=src[0]))
        except OSError as err:
            log(str(err) + " for {name}".format(name=src[0]))
        except paramiko.AuthenticationException as err:
            log(str(err) + " for {name}".format(name=src[0]))
    return redirect(url_for('main'))


@app.route('/post/router/delete', methods=['POST'])
def delete_router():
    router = request.form.get("router")
    s = g.database.delete_router(router)
    logging.debug(s)
    print(s)
    return s


@app.route('/post/forwarding/delete', methods=['POST'])
def delete_forwarding():
    port = request.form.get("ext_p")
    s = g.database.delete_forwarding(port)
    logging.debug(s)
    print(s)
    return s


app.run(host='0.0.0.0')
