class FDataBase:

    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

    def getReportList(self, params={}):
        conditions = []
        if 'id' in params and len(params['id']):
            conditions.append(f"kambala_id LIKE '%{params['id']}%'")
        if 'ok_only' in params and params['ok_only'] == 'y':
            conditions.append(f"errors_cnt == 0")
        where = ' WHERE ' + " and ".join(conditions) if len(conditions) else ''
        lim = f"LIMIT {params['limit']}" if 'limit' in params else ''
        sql = f"SELECT * FROM reports {where} ORDER BY date_create DESC {lim}"
        print(sql)
        return self.esql(sql)

    def getReport(self, kampure, unixtime):
        sql = f'''SELECT * FROM reports WHERE kambala_id == '{kampure}' AND date_create == {unixtime}'''
        report_obj = self.esql(sql, one=True)
        return report_obj

    def esql(self, sql, one=False):
        try:
            self.__cur.execute(sql)
            result = self.__cur.fetchone() if one else self.__cur.fetchall()
            if result:
                return result
        except Exception as e:
            print('DB reading error: ', str(e))
        return []
