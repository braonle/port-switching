# *!*/usr/bin/python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, abort
import paramiko
from configparser import ConfigParser
import logging
import ipaddress
from peewee import *

# DEB: /etc/default/iptables
# RPM: /etc/sysconfig/iptables

db = SqliteDatabase('database.s3db')


class Router(Model):
    extern_ip = TextField(unique=True)
    name = TextField(null=False, unique=True)

    class Meta:
        database = db
        db_table = 'routers'


class Forwarding(Model):
    extern_port = IntegerField(unique=True)
    intern_ip = TextField(null=False)
    intern_port = IntegerField(null=False)

    class Meta:
        database = db
        db_table = 'forwarding'
        constraints = [SQL('UNIQUE(intern_ip, intern_port)')]


class FlashHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            with app.test_request_context():
                flash(self.format(record))
        except:
            self.handleError(record)

app = Flask(__name__)
app.config.from_pyfile('flask_conf.py')
parser = ConfigParser()
parser.read(filenames='settings.conf')

# TODO logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

h = logging.StreamHandler()
h.setLevel(level=logging.INFO)
fm = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
h.setFormatter(fmt=fm)
logger.addHandler(h)

h = logging.FileHandler(filename='log.txt', mode='a', encoding='UTF-8')
h.setLevel(level=logging.DEBUG)
fm = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
h.setFormatter(fmt=fm)
logger.addHandler(h)

logger.info('Starting application')


@app.route('/')
def main():
    db.connect()
    rt = [{'name': router.name, 'ext_ip': router.extern_ip}
          for router in Router.select().order_by(Router.name)]
    sw = [{'ext_p': fwd.extern_port, 'ip': fwd.intern_ip, 'int_p': fwd.intern_port}
          for fwd in Forwarding.select().order_by(Forwarding.extern_port)]
    db.close()
    maxhost = 9
    for i in rt:
        if len(i['name']) > maxhost:
            maxhost = len(i['name'])
    return render_template('main.html', routers=rt, forwarding=sw, hsize=maxhost,
                           title='Main page')


@app.route('/get/routers/edit')
def redirect_edit_router(**kwargs):
    # Initial request for router editing
    if len(kwargs) == 0:
        name = request.args.get('name')
        db.connect()
        try:
            res = Router.get(Router.name == name)
        except Router.DoesNotExist:
            return abort(404)
        finally:
            db.close()
    # This routing is issued from edit_router() due to bad parameters
    else:
        res = kwargs['res']
        name = kwargs['name']
    return render_template('edit_router.html', name=name, ip=res.extern_ip, new_name=res.name,
                           title='Edit {name}'.format(name=res.name))


@app.route('/get/forwarding/edit')
def redirect_edit_forwarding(**kwargs):
    # Initial request for forwarding rules editing
    if len(kwargs) == 0:
        port = request.args.get('port')
        db.connect()
        try:
            res = Forwarding.get(Forwarding.extern_port == port)
        except Forwarding.DoesNotExist:
            return abort(404)
        finally:
            db.close()
    # This routing is issued from edit_forwarding() due to bad parameters
    else:
        res = kwargs['res']
        port = kwargs['port']
    return render_template('edit_forwarding.html', ext_p=res.extern_port,
                           ip=res.intern_ip, int_p=res.intern_port,
                           port=port, title='Edit {name}'.format(name=res.extern_port))


@app.route('/post/routers/edit/<string:name>', methods=['POST'])
def edit_router(name):
    """Checks input values' validity, thus saving data or discarding them"""
    ip = request.form.get('ip')
    new_name = request.form.get('new_name')
    flg = False
    try:
        net = ipaddress.ip_address(ip)
    except ValueError:
        net = None
    if len(new_name) == 0:
        flash("Empty name")
        flg = True
    if net is None:
        flash("Bad IP address")
        flg = True

    if flg:
        return redirect_edit_router(res=Router(name=name, extern_ip=ip), name=new_name)
    else:
        rt = Router.get(Router.name == name)
        rt.name = new_name
        rt.extern_ip = ip
        msg = "{router} -> {name} : {ip} changed".format(router=name, name=new_name, ip=ip)
        flg = False
        db.connect()
        try:
            rt.save()
        except IntegrityError as err:
            msg = str(err)
            flg = True
        finally:
            db.close()
            logger.info(msg)
            flash(msg)
        if flg:
            return redirect_edit_router(res=rt, name=name)
    return redirect(url_for('main'))


@app.route('/post/forwarding/edit/<int:port>', methods=['POST'])
def edit_forwarding(port):
    """Checks input values' validity, thus saving data or discarding them"""
    ext_p = request.form.get('ext_p')
    ip = request.form.get('ip')
    int_p = request.form.get('int_p')
    flg = False
    try:
        net = ipaddress.ip_address(ip)
    except ValueError:
        net = None
    if not ext_p.isdigit() or not 1 <= int(ext_p) <= 65535:
        flash("Bad external port")
        flg = True
    if not int_p.isdigit() or not 1 <= int(int_p) <= 65535:
        flash("Bad internal port")
        flg = True
    if net is None:
        flash("Bad IP address")
        flg = True
    if flg:
        return redirect_edit_forwarding(res=Forwarding(extern_port=ext_p,
                                                   intern_ip=ip,
                                                   intern_port=int_p),
                                        port=port)
    else:
        fwd = Forwarding.get(Forwarding.extern_port == port)
        fwd.extern_port = ext_p
        fwd.intern_ip = ip
        fwd.intern_port = int_p
        msg = "{port} -> {new_ep} into {ip}:{new_p}".format(
                port=port, new_ep=ext_p, ip=ip, new_p=int_p)
        flg = False
        db.connect()
        try:
            fwd.save()
        except IntegrityError as err:
            msg = str(err)
            flg = True
        finally:
            db.close()
            logger.info(msg)
            flash(msg)
        if flg:
            return redirect_edit_forwarding(res=fwd, port=port)
    return redirect(url_for('main'))


@app.route('/get/routers/add')
def add_router_red(**kwargs):
    param = kwargs.get('param')
    # Case of initial page load; otherwise parameters
    # are returned by add_router for displaying or editing
    if param is None:
        param = Router(name='', extern_ip='')
    return render_template('add_router.html', name=param.name,
                           add=param.extern_ip, title='Add router')


@app.route('/get/forwarding/add')
def add_forwarding_red(**kwargs):
    param = kwargs.get('param')
    # Case of initial page load; otherwise some parameters
    # are returned by add_forwarding for displaying or editing
    if param is None:
        param = Forwarding(extern_port='', intern_ip='', intern_port='')
    return render_template('add_forwarding.html', ep=param.extern_port,
                           ip=param.intern_ip, p=param.intern_port,
                           title='Add forwarding')


@app.route('/post/routers/add', methods=['POST'])
def add_router():
    """Checks input values' validity, thus saving data or discarding them"""
    name = request.form.get('name')
    ip = request.form.get('ip')
    flg = False
    try:
        net = ipaddress.ip_address(ip)
    except ValueError:
        net = None
    if len(name) == 0:
        flash('No name supplied')
        flg = True
    if net is None:
        flash("Bad IP address")
        flg = True
    if flg:
        return add_router_red(param=Router(name=name, extern_ip=ip))
    else:
        msg = "{name} : {addr} added".format(name=name, addr=ip)
        db.connect()
        flg = False
        try:
            Router.create(name=name, extern_ip=ip)
        except IntegrityError as err:
            msg = str(err)
            flg = True
        finally:
            db.close()
            logger.info(msg)
            flash(msg)
        if flg:
            return add_router_red(param=Router(name=name, extern_ip=ip))
    return redirect(url_for('main'))


@app.route('/post/forwarding/add', methods=['POST'])
def add_forwarding():
    """Checks input values' validity, thus saving data or discarding them"""
    ext_p = request.form.get('ext_p')
    ip = request.form.get('ip')
    int_p = request.form.get('int_p')
    flg = False
    try:
        net = ipaddress.ip_address(ip)
    except ValueError:
        net = None
    if not ext_p.isdigit() or not 1 <= int(ext_p) <= 65535:
        flash("Bad external port")
        flg = True
    if net is None:
        flash("Bad IP address")
        flg = True
    if not int_p.isdigit() or not 1 <= int(int_p) <= 65535:
        flash("Bad internal port")
        flg = True
    if flg:
        return add_forwarding_red(param=Forwarding(extern_port=ext_p, intern_ip=ip,
                                                   intern_port=int_p))
    else:
        msg = "forwarding rule {ext_port} -> {ip}:{int_port} added".format(
                ext_port=ext_p, ip=ip, int_port=int_p)
        flg = False
        db.connect()
        try:
            Forwarding.create(extern_port=ext_p, intern_ip=ip, intern_port=int_p)
        except IntegrityError as err:
            flg = True
            msg = str(err)
        finally:
            db.close()
            logger.info(msg)
            flash(msg)
        if flg:
            return add_forwarding_red(param=Forwarding(extern_port=ext_p, intern_ip=ip, intern_port=int_p))
    return redirect(url_for('main'))


def ssh_single(ip):
    """Handles a delivery of forwarding rules to a specified host"""
    parser.read(filenames='settings.conf')
    path = parser.get(section="SSH", option="path")
    output_if = parser.get(section="SSH", option="output_if")
    input_if = parser.get(section="SSH", option="input_if")
    ssh_port = parser.getint(section="SSH", option="port")
    login = parser.get(section="SSH", option="login")
    timeout = int(parser.get(section="SSH", option="timeout"))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.RSAKey.from_private_key_file(parser.get(section="SSH", option="keyfile"))
    client.connect(hostname=ip, username=login, pkey=key, port=ssh_port, timeout=timeout)
    ftp_client = client.open_sftp()
    file = ftp_client.open(path, "w")
    res = [{'ext_p': line.extern_port, 'ip': line.intern_ip,
            'p': line.intern_port} for line in Forwarding.select()]
    file.writelines(render_template('iptables_template',
                                    param=res, out_if=output_if, in_if=input_if, ext_ip=ip))
    file.flush()
    file.close()
    ftp_client.close()
    client.exec_command('iptables-restore < {path}'.format(path=path))
    client.close()


@app.route('/get/ssh/send/<string:router>')
def ssh_send(router):
    """Handles a delivery of forwarding rules to the specified router"""
    try:
        rt = Router.get(Router.name == router)
        ssh_single(rt.extern_ip)
        flash("Successful sending for {name}".format(name=router))
        logger.info("Successful sending for {name}".format(name=router))
    except OSError as err:
        flash(str(err) + " for {name}".format(name=router))
    except paramiko.AuthenticationException as err:
        flash(str(err) + " for {name}".format(name=router))
    except DoesNotExist:
        return abort(404)
    return redirect(url_for('main'))


@app.route('/get/ssh/send_all')
def ssh_send_all():
    """Handles a delivery of forwarding rules to all routers"""
    for src in Router.select():
        try:
            ssh_single(src.extern_ip)
            flash("Successful sending for {name}".format(name=src.name))
            logger.info("Successful sending for {name}".format(name=src.name))
        except OSError as err:
            flash(str(err) + " for {name}".format(name=src.name))
        except paramiko.AuthenticationException as err:
            flash(str(err) + " for {name}".format(name=src.name))
    return redirect(url_for('main'))


@app.route('/delete/router', methods=['DELETE'])
def delete_router():
    router = request.form.get("router")
    s = "Router {name} deleted".format(name=router)
    try:
        ret = Router.get(Router.name == router)
        ret.delete_instance()
    except DoesNotExist:
        s = 'Router does not exist'
    logger.info(s)
    return s


@app.route('/delete/forwarding', methods=['DELETE'])
def delete_forwarding():
    port = request.form.get("ext_p")
    s = "forwarding rule for {port} deleted".format(port=port)
    try:
        ret = Forwarding.get(Forwarding.extern_port == port)
        ret.delete_instance()
    except DoesNotExist:
        s = 'Forwarding rule does not exist'
    logger.info(s)
    return s


app.run(host='0.0.0.0', threaded=True)

logger.info('Terminating application')
