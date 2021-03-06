import sqlite3
from configparser import ConfigParser


class DBHandler:
    def __init__(self, conf):
        # Configuration load
        # Используем парсер, чтобы не вытаскивать параметры руками
        self.parser = ConfigParser()
        self.parser.read(filenames=conf)

        # Parameters initialization
        self.strings = {}
        self.conn = None

        # Initializing specifics for databases
        # Есть SQLite3 и PostgreSQL, например. У них разная передача параметров ((?,?) и (%s, %s))
        # в запросе, плюс разные библиотеки использовать надо. Чтобы не плодить if'ы, можно сделать
        # map, в него засунуть ключи и функции, инициализирующие базу. А дальше просто этот обработчик
        # вызывать, если он не предусмотрен - ругаться.
        conns = self.__handlers_init()
        conn_init = conns.get(self.parser.get(section="DATABASE", option="type"), None)
        if conn_init is not None:
            conn_init()
        else:
            raise AttributeError("Not supported DB type")

    def __handlers_init(self):
        conns = {'sqlite3': self.__sqlite3_init}
        return conns

    def __sqlite3_init(self):
        self.conn = sqlite3.connect(database=self.parser.get(section="DATABASE", option="database"))
        self.strings['add_router'] = "INSERT INTO routers VALUES(?,?)"
        self.strings['add_switching'] = "INSERT INTO switching VALUES(?,?,?)"
        self.strings['select_routers'] = "SELECT name, extern_ip from routers"
        self.strings['select_router'] = "SELECT name, extern_ip from routers WHERE name = ?"
        self.strings['select_switchings'] = "SELECT extern_port, intern_ip, intern_port from switching"
        self.strings['select_switching'] = "SELECT extern_port, intern_ip, intern_port from switching WHERE " \
                                           "extern_port = ?"
        self.strings['edit_router'] = "UPDATE routers SET name = ?, extern_ip = ? WHERE name = ?"
        self.strings['edit_switching'] = "UPDATE switching SET extern_port = ?, intern_ip = ?," \
                                         "intern_port = ? WHERE extern_port = ?"
        self.strings['delete_router'] = "DELETE from routers WHERE name = ?"
        self.strings['delete_switching'] = "DELETE from switching WHERE extern_port = ?"

    def add_router(self, name, ext_ip):
        try:
            self.conn.cursor().execute(self.strings['add_router'], (ext_ip, name))
            self.conn.commit()
            res = "Success: {name} : {addr} added".format(name=name, addr=ext_ip)
        except sqlite3.IntegrityError as err:
            res = err.__str__()
        return res

    def add_switching(self, ext_port, int_ip, int_port):
        try:
            self.conn.cursor().execute(self.strings['add_switching'], (ext_port, int_ip, int_port))
            self.conn.commit()
            res = "Success: switching rule {ext_port} -> {ip}:{int_port} added".format(
                ext_port=ext_port, ip=int_ip, int_port=int_port)
        except sqlite3.IntegrityError as err:
            res = err.__str__()
        return res

    # For web table of routers
    def get_routers(self):
        res = []
        cur = self.conn.cursor()
        cur.execute(self.strings['select_routers'])
        for line in cur.fetchall():
            (name, eip) = line
            res.append((name, eip))
        return res

    # For web table of switching rules
    def get_switchings(self):
        res = []
        cur = self.conn.cursor()
        cur.execute(self.strings['select_switchings'])
        for line in cur.fetchall():
            (ep, ip, p) = line
            res.append((int(ep), ip, int(p)))
        return res

    def get_router(self, router):
        cur = self.conn.cursor()
        cur.execute(self.strings['select_router'], (router,))
        (name, eip) = cur.fetchone()
        return name, eip

    def get_switching(self, port):
        cur = self.conn.cursor()
        cur.execute(self.strings['select_switching'], (port,))
        (ep, ip, p) = cur.fetchone()
        return ep, ip, p

    def edit_router(self, router, ip, name):
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['edit_router'], (name, ip, router))
            self.conn.commit()
            res = "{router} -> {name} : {ip} changed".format(router=router, name=name, ip=ip)
        except sqlite3.IntegrityError as err:
            res = err.__str__()
        return res

    def edit_switching(self, port, new_ep, ip, new_p):
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['edit_switching'], (new_ep, ip, new_p, port))
            self.conn.commit()
            res = "{port} -> {new_ep} into {ip}:{new_p}".format(
                port=port, new_ep=new_ep, ip=ip, new_p=new_p)
        except sqlite3.IntegrityError as err:
            res = err.__str__()
        return res

    def delete_router(self, name):
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['delete_router'], (name,))
            self.conn.commit()
            res = "Router {name} deleted".format(name=name)
        except sqlite3.IntegrityError as err:
            res = err.__str__()
        return res

    def delete_switching(self, port):
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['delete_switching'], (port,))
            self.conn.commit()
            res = "Switching rule for {port} deleted".format(port=port)
        except sqlite3.IntegrityError as err:
            res = err.__str__()
        return res

    def __del__(self):
        self.conn.close()
