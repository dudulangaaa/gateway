'''
run single A-Stock 603997, version 3
gate for list_0 let in
all other conditions apply following, sequentially -> buy list
'''
from collections import OrderedDict
import pytz
from datetime import timedelta
# from zipline import TradingAlgorithm
# from gateway.algorithm import TradingAlgorithm
from gateway import TradingAlgorithm

import pandas as pd
from zipline.api import (order, symbol)
import numpy as np
import re

from cn_calendar.gateway.exchange_calendar_shsz import SHSZExchangeCalendar

import sys
import logbook
# logging setup
if True :
    # handler = logbook.StreamHandler(sys.stdout, level=logbook.INFO)
    # handler.formatter.format_string = '{record.time}|{record.level_name}|{record.filename}|{record.module}|{record.func_name}|{record.lineno}|{record.message}'
    handler = logbook.StreamHandler(sys.stdout, level=logbook.DEBUG)
    handler.formatter.format_string = '{record.time}|{record.level_name}|{record.module}|{record.func_name}|{record.lineno}|{record.message}'
    handler.push_application()
    log = logbook.Logger("zipline_astock01")
    # or using this : with handler.applicationbound():

if True:
    from pandas_datareader.google.daily import GoogleDailyReader
    @property
    def url(self):
        print("call @property get url, %s, %s" % (self, type(self)))
        return 'http://finance.google.com/finance/historical'
    GoogleDailyReader.url = url

if True :
    # sn : serial number, or step number,  unit is handle_data's time span
    #    initial start sn
    # span : total sn in this batch, define moving rolling window [sn, sn + span)
    #       span should be 2x of actual requirement for optimzation
    #       span/2 tomoving upper..
    class Batch :
        def __init__(self, base_sn, symbols, factor_names, span):
            self.base_sn = base_sn
            self.span = span
            self.window_size = span * 2 + 1
            self.factors = {}
            for factor in factor_names :
                df = pd.DataFrame(np.zeros((self.window_size, len(symbols))), index=range(base_sn, base_sn + self.window_size), columns=symbols)
                self.factors[factor] = df
            self.symbols = symbols;
            self.watch_lists = {}   # or move this list to stetegy? we may have multiple Batch??
            self.orders = []
                # each items as dict format : 'sn', 'type"/buy or sell, 'symbol', 'volume'
            pass

        # name : watch_lists name
        # until_sn : get all symbols until this sn
        # return : symbol list in the list until_sn
        def get_watch_list_at(self, name, pos) :
            assert pos <= 0, "get_watch_list_at, pos %d must <= 0"%pos
            until_sn = self.current_sn + pos
            ret = set()
            if name in self.watch_lists :
                for sn, l in self.watch_lists[name].items() :
                    if sn == until_sn :
                        ret.update(l);
            return list(ret)

        def get_watch_list(self, name, pos) :
            assert pos <= 0, "get_watch_list, pos %d must <= 0"%pos
            until_sn = self.current_sn + pos
            ret = set()
            if name in self.watch_lists :
                for sn, l in self.watch_lists[name].items() :
                    if sn <= until_sn :
                        ret.update(l);
            return list(ret)

        def set_watch_list(self, name, watch_list) :
            self.watch_lists[name] = {self.current_sn : watch_list}
            pass

        def add_watch_list(self, name, watch_list) :
            self.watch_lists[name][self.current_sn] = watch_list
            pass

        def reset_watch_list(self, name) :
            self.watch_lists[name] = {}

        def dump(self):
            print("batch base_sn : %d"%self.base_sn)
            print("span : %d, window_size : %d"%(self.span, self.window_size))
            print("current_sn : %d"%(self.current_sn))
            print("symbols : %s"%self.symbols)
            for name, factor in self.factors.items() :
                print("factor name %s, value :\n%s"%(name, factor))
            for name, wl in self.watch_lists.items() :
                print("watchlie %s, value :\n%s"%(name, wl))

        def prepare(self, sn, data):
            '''
            calculate neccessary factor we need
            :param data:
                data is passed as parameter of handle_data
            :return:
            '''
            # print("sn %d, prepare data for %d"%(sn, self.sn))
            # rolling watch_list, remove old (current_sn - sn > 60) ones
            idx = sn - self.base_sn
            if idx + 1 == self.window_size :    # current windows is full, clean first half and rolling up
                size = self.span    # int(self.window_size / 2 - 1)    # rollling size
                log.info("rolling window at size %d"%size)

                current_end_sn = self.base_sn + self.window_size
                new_base_sn = self.base_sn + size
                new_end_sn = new_base_sn + self.window_size
                log.info("rolling from [%d %d] to [%d %d]"%(self.base_sn, current_end_sn, new_base_sn, new_end_sn))
                for factor, df in self.factors.items() :
                    new_df = pd.DataFrame(np.zeros((new_end_sn - current_end_sn, len(self.symbols))), \
                                          index=range(current_end_sn, new_end_sn), columns=self.symbols)
                    self.factors[factor] = pd.concat([ df.loc[range(new_base_sn, current_end_sn)], new_df ])
                    pass

                self.base_sn = new_base_sn
                idx = sn - self.base_sn
                self.set_watch_list("ALL", self.symbols)
                pass

            # prepare watch list
            for n, l in self.watch_lists.items() :
                remove_sns = [ i for i in l.keys() if i + self.span < sn ]
                if remove_sns : # if not empty
                    log.info("remove from list %s, sn : %s"%(n, remove_sns))
                    for s in remove_sns :
                        del l[s]

            assert idx + 1 <= self.window_size, "current index %d + 1 must <= window_size %d"%(idx, self.window_size)
            for name, df in self.factors.items() :
                if name == 'sma5' :
                    df.iloc[idx] = data.history(self.symbols, "close", 5, '1m').mean()
                    pass
                elif name == 'sma20' :
                    df.iloc[idx] = data.history(self.symbols, "close", 20, '1m').mean()
                    pass
                elif name == 'slope5' :
                    # calculate slope in previous 5 points
                    pass

            self.current_data = data
            self.current_sn = sn
            pass

        # todo : get_watch_list_param_hist(self, watch_list, name, from , to)
        def get_watch_list_param(self, watch_list, name, pos) :
            assert watch_list in self.watch_lists, "watch_list %s must be in watch_lists [%s]"%(watch_list, self.watch_lists.keys())
            symbols = set()
            for sn, l in self.watch_lists[watch_list].items() :
                symbols.update(l);
            # log.info("symbols %s"%symbols)
            # log.info("get name %s pos %d : %s"%(name, pos, self.get(name, pos)))
            # log.info("get name %s pos %d type : %s"%(name, pos, type(self.get(name, pos))))
            return self.get(name, pos)[list(symbols)];
            pass

        # todo : get_hist(self, name, from, to)
        def get(self, name, pos) :
            assert pos <= 0, "batch get() pos (%d) must <= 0"%pos
            params = ['sma5', 'sma20', 'price']
            assert name in params, 'name %s must be within params [%s]'%(name, params)
            #  total sn   4      1 2 3 4
            #                    |--------- 1  base_sn
            #                          | -- 4  current_sn, idx = 3
            # if pos = -1            | -----3, pos -1, , idx = 2
            idx = self.current_sn - self.base_sn + pos
            assert idx < self.window_size, \
                "idx %d (from pos %d) must < window_size %d"%(idx, pos, self.window_size)
            if name == 'price' :
                return self.current_data.history(self.symbols, 'close', 1 - pos, '1d').iloc[0]
                pass
            elif name == 'sma5' :
                return self.factors['sma5'].iloc[idx]
                pass
            elif name == 'sma20' :
                return self.factors['sma20'].iloc[idx]
                pass

stocks = ['601336']

def initialize(context):
    context.symbols = [symbol(s) for s in stocks]
    context.sn = 0
    batch = Batch(context.sn + 1, context.symbols, ("sma5", "sma20"), 30)
    context.batch = batch
    # context.strategy = createStrategy(createStatements())
    context.strategy = createStrategy(createStatements())
    context.strategy.initialize(context.batch)
    pass

def handle_data(context, data):
    sn = context.sn
    sn = sn + 1
    context.sn = sn

    if True :
        # pc = data.current(context.symbols, 'close')
        # print("current : \n%s"%pc)
        pass

    if sn < 25  or sn > 1000:
        return

    log.info("-------- SN %d -----------, date : %s"%(sn, data.current_dt))
    if True :
        if sn == 99 or (sn > 120 and sn<130) :       # for debug/testing only
            # context.batch.dump();
            print("history 5 : \n%s"%data.history(context.symbols, 'close', 5, '1m'))

    if False :
        log.info("-------- SN %d -----------, date : %s"%(sn, data.current_dt))
        prepare_batch(sn, context, data)
        if True :
            if sn == 99 :       # for debug/testing only
                context.batch.dump();
                print("history 5 : \n%s"%data.history(context.symbols, 'close', 5, '1m'))
                # print("current : \n%s"%data.current(context.symbols, 'close'))

        if False :
            # strategy = context.strategy
            # context.strategy.perform(context.batch)     # will call order or sell
            context.strategy.perform2(context.batch)     # will call order or sell

            buy_list = context.batch.get_watch_list_at('buy', 0);
            log.info("buy list : %s"%buy_list)
            sell_list = context.batch.get_watch_list_at('sell', 0);
            log.info("sell list : %s"%sell_list)

            buy_list = list(set(buy_list) - set(sell_list))
            log.info("adjust buy list : %s"%buy_list)

            for s in buy_list :
                log.info("buy order 10 : %s"%s)
                order(s, 10)
            for s in sell_list :
                log.info("sell order -10 : %s"%s)
                order(s, -10)

            # log.info("get watch list buy: %s"%context.batch.watch_lists['buy'])
            # log.info("get watch list param, buy, price, 0 : %s"%context.batch.get_watch_list_param('buy', 'price', 0))



            ##################################################################
            # for debug only
            if sn == 99 :       # for debug/testing only
                context.batch.dump();
                print("history 5 : \n%s"%data.history(context.symbols, 'close', 5, '1d'))
                print("current : \n%s"%data.current(context.symbols, 'close'))

            if False and sn >= 28 :
                print("portfolio, %s"%context.portfolio)
                order(context.symbols[0], 10)

    # test Factor
    ##################################################################

def prepare_batch(sn, context, data) :
    batch = context.batch;
    print("prepare_batch, sn %d, batch base_sn %d"%(sn, batch.base_sn))
    batch.prepare(sn, data);
    # todo : check batch base_sn and sn, remove/rolling 1/2 span upward
    # todo : check batch's watchlist, remove symbols old than span

class Strategy() :
    def __init__(self, procedures):
        self.procedures = procedures
        self.total_proces = len(procedures)
        for i, p in enumerate(self.procedures) :
            log.info("procecure : %d"%i)
            dump_proc(p)

        pass

    def initialize(self, batch) :
        log.info("Strategy init batch, setup watchlist")
        batch.watch_lists = {};
        for p in self.procedures :
            batch.watch_lists[p['input']] = {}
            batch.watch_lists[p['output']] = {}
        log.info("build watchlist : %s"%batch.watch_lists)

    def perform(self, batch) :
        ## leave here for reference
        #    try :
        #        x = eval(statement)
        #        print("eval statement : %s, result : %s, type %s"%(statement, x, type(x)));
        #    except Exception as e :
        #        print("eval statement : %s"%statement);
        #        raise e
        watch_lists = batch.watch_lists
        current_sn = batch.current_sn

        # gate to list_0
        ALL = batch.symbols
        batch.set_watch_list('ALL', ALL)
        ### condition to check ######
        x = batch.get('sma20', 0)[ALL] > batch.get('price', 0)[ALL]
        log.info("sn %d, x gate, first list one : %s"%(batch.current_sn, x))
        list_0 = [ALL[i] for i, b in enumerate(x) if b == True]
        log.info("list_0 : : %s"%list_0)
        batch.add_watch_list('list_0', list_0);

        # batch.get_watch_lists(name, until_sn)
        list_0 = batch.get_watch_list('list_0', 0)
        log.info("current list_0 from all : %s"%list_0)
        y = batch.get('sma5', 0)[list_0] > batch.get('price', 0)[list_0]
        log.info("sn %d, y filter, to list_1 : %s"%(current_sn, y))
        list_1 = [ALL[i] for i, b in enumerate(y) if b == True]
        batch.set_watch_list('list_1', list_1)

        # to buy list
        list_1 = batch.get_watch_list('list_1', 0)
        log.info("current list_1 from all : %s"%list_1)
        z = batch.get('sma5', -1)[list_1] > batch.get('price', 0)[list_1]
        log.info("sn %d, y filter, to buy %s"%(current_sn, z))
        buy = [ALL[i] for i, b in enumerate(z) if b == True]
        # batch.reset_watch_list('buy')
        batch.add_watch_list('buy', buy)

        # order something
        for s in buy :
            print("sn %d, order %s, volume %d"%(current_sn, s, 10))
            order(s, 10)
        # batch.current_sn
        pass

    def perform2(self, batch) :
        for proc in self.procedures :
            dump_proc(proc)
            input = proc['input']
            output = proc['output']
            input_watch_list = batch.get_watch_list(input, 0)
            log.info("input watch list %s : [%s]"%(input, input_watch_list))
            if len(input_watch_list) < 1 :
                log.info("input watch list empty : %s"%input)
                continue;
            # no need - output_watch_list = batch.get_watch_list(output)
            condition = proc['condition'];
            x = eval(condition)     # this is the result in input_watch_list
            result = [input_watch_list[i] for i, b in enumerate(x) if b == True]
            log.info("eval result : %s"%x)
            log.info("eval result symbols : %s"%result)
            if proc['output_method'] == 'set' :
                batch.set_watch_list(output, result)
            else : # 'add'
                batch.add_watch_list(output, result)
        pass

## leave here for reference
#    try :
#        x = eval(statement)
#        print("eval statement : %s, result : %s, type %s"%(statement, x, type(x)));
#    except Exception as e :
#        print("eval statement : %s"%statement);
#        raise e
# match expressiong
# example : sma[0] - 0.5
# match = re.match(r' *(\w+)\[(\d+)\]( *[+\-\*/] *\d+(\.\d+)*)', expr)
# self.eval_expr = "batch.get('%s', %s) %s"%(match.group(1), match.group(2), match.group(3));

def createStrategy(str) :
    '''
    example statements :
        'sma5[0] + price[-1] > sma20[0] + 2'
    been translated to :
        batch.get("sma5", 0) + batch.get("price", -1) > batch.get("sma20", 0) + 2
    :param statements:
    :return:
    '''
    procedures = []
    statements = str.splitlines()
    inputs = set()
    outputs = set()
    for i, s in enumerate(statements):
        log.info("%2d statement : %s"%(i, s))
        # t = re.sub(r'([^\d\W]\w*)\[([-]*\d+)\]', r'batch.get("\1", \2)', s)
        # t = t.strip()
        if s.startswith("#") or s.strip() == "":
            log.info("comments or empty, pass")
            continue;
        ss = s.split(",")

        def parse_output(s) :
            log.info("parse_io : %s"%s)
            match = re.match(r'(add|set) +(.*)', s)
            return match.group(1), match.group(2)

        proc = {}
        proc['name'] = ss[0].strip()
        proc['type'] = ss[1].strip()
        proc['input'] = ss[2].strip()
        t = re.sub(r'([^\d\W]\w*)\[([-]*\d+)\]', r'batch.get_watch_list_param(LIST, "\1", \2)', ss[3])
        t = re.sub(r'LIST', "'%s'"%proc['input'], t)
        proc['condition'] = t
        # proc['output'] = ss[4].strip()
        log.info("try to parse output : %s"%ss[4].strip())
        proc['output_method'], proc['output'] = parse_output(ss[4].strip())
        dump_proc(proc)
        inputs.add(proc['input'])
        outputs.add(proc['output'])
        procedures.append(proc)

    log.info("total input : %s"%inputs)
    log.info("total output : %s"%outputs)

    return Strategy(procedures)

def dump_proc(proc) :
    assert proc['type'] in ['filter', 'gate'], "proc type %s must be 'filter' or 'gate'"%proc['type']
    log.info("proc name %s, type %s, input : %s, output : %s %s, condition %s" \
             %(proc['name'], proc['type'], proc['input'], proc['output_method'], proc['output'], proc['condition']))
    pass

def createStatements() :
    return \
'''
# comment line, ignore (emtpy line ignor either)
# buy and bought are two special list
# proposed scripting :
0, gate, ALL  ,   (sma20[0] > price[0]), add list_0
# 0, filter, list_0, (slope5[0] > -0.1 and slope5[0] < 0.1),  set list_1
0, filter, list_0, (sma5[0] > sma20[0]),  add buy
0, filter, buy, (price[-2] > price[-1]) & (price[-1] > price[0]), add sell
# 0, filter, buy, (price[-1] > price[0]), add sell
'''

if __name__ == '__main__' :
    if False :
        log.info("do some testing ONLY")
        createStrategy(createStatements())
        quit()

    log.info("it's __main__, do something")

    log.info('load data')
    data = OrderedDict()
    # df = pd.read_csv('data/603997.csv', index_col='date', parse_dates=['date']).tail(2770)
    # df = pd.read_csv('data/603997.csv', index_col='date', parse_dates=['date']).tail(100)
    # df = pd.read_csv('data/StockPrice_5Min_Subset.csv', index_col='date', parse_dates=['date']).tail(100)
    df = pd.read_csv('data/601336.SH.csv', index_col='time', parse_dates=['time']) #.tail(100)
    df.rename(columns={'time' : 'date'}, inplace=True)
    df['test'] = [i for i in range(len(df.index))]
    log.info(df.columns)
    log.info(df.head(5))
    log.info(df.index)
    data['601336'] = df
    panel = pd.Panel(data)

    cn_cal = SHSZExchangeCalendar()
    panel.major_axis = panel.major_axis.tz_localize(cn_cal.tz)
    algo_obj = TradingAlgorithm(initialize=initialize, handle_data=handle_data,
                                trading_calendar = cn_cal,
                                data_frequency = 'minute',
                                clock_file = "data/clock.csv")

    log.info('run algorithm')
    perf_manual = algo_obj.run(panel)
    if False :
        print(perf_manual)

    if False :
        import pickle
        file = "e:\\perf.p"
        log.info("write performance to pickle : %s"%file)
        pickle.dump(perf_manual, open(file, 'wb'))

    log.info('done')
