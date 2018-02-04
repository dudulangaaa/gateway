'''
general utility, implement watch lists management
'''

###############################################################################################
# WatchLists Setup & Defines Watch List functions:
# WatchLists is defined for each trading decision, and created when needed while setting up the strategy.
#
# Example:
#
#             watchlist_names              : vector/list of WatchList names provided by user.
#             tickers                                  : pass the list of tickers for the strategy.
#             base_sn               : defines the starting index/step number when list created.
#             trading_window               : optional, determines the length of the trading cycle.
###############################################################################################

import sys
import logbook
log = logbook.Logger("app01")

class WatchList :
    def __init__(self, name):
        self.data = {}      # {sn : { set of tickers } }
        self.name = name
        pass

    def __str__(self) :
        s = []
        s.append("watchlist, name %s :"%(self.name))
        for sn in sorted(self.data.keys()) :
            s.append("sn %d, %s"%(sn, sorted(self.data[sn])))
        return '\n'.join(s)

    def add(self, sn, tickers) :
        if sn in self.data :
            self.data[sn].update(tickers)
        else :
            self.data[sn] = set(tickers)
        pass

    def set(self, sn, tickers) :
        self.data[sn] = set(tickers)
        pass

    def get(self, sn) :
        if sn not in self.data :
            return set()
        else :
            return self.data[sn]

    def get_until(self, sn) :
        tickers = set()
        for k in self.data :
            if k <= sn :
                tickers = tickers | self.data[k]
        return tickers

    def reset(self, sn = None, tickers = None) :
        self.data = {}
        if sn != None and tickers != None :
            self.data[sn] = set(tickers)

    def cut(self, cut_sn) :
        cuts = [ sn for sn in self.data.keys() if sn <= cut_sn ]
        for sn in cuts :
            del self.data[sn]

class WatchListConst(WatchList) :
    def __init__(self, name, tickers):
        self.data = set(tickers);
        self.name = name
        pass

    def __str__(self) :
        s = []
        l = list(self.data)
        l.sort()
        s.append("watchlist, name %s : %s"%(self.name, l))
        return '\n'.join(s)

    def add(self, *args) :
        # log.warn("WatchListConst add N/A")
        pass

    def set(self, *args) :
        # log.warn("WatchListConst set N/A")
        pass

    def reset(self, *args) :
        # log.warn("WatchListConst reset N/A")
        pass

    def cut(self, *args) :
        # log.warn("WatchListConst cut N/A")
        pass

class WatchLists :
    '''
    watch lists management
    '''

    def __init__(self, watchlist_names, tickers, base_sn=0, trading_window=None, watchList_relation=None):
        # { name : { sn : [tickers...] } }
        self.watchlists = {}
        self.watchlist_names = watchlist_names
        for i, n in enumerate(self.watchlist_names) :
            if i == 0 :
                self.watchlists[n] = WatchListConst(n, tickers)
            else :
                self.watchlists[n] = WatchList(n)

        self.tickers = tickers
        self.base_sn = base_sn
        self.trading_window =trading_window
        self.watchlist_relation = watchList_relation
        self.sn = base_sn
        pass

    def __str__(self) :
        s = []
        s.append("watchlists : ")
        s.append("tickers         : %s"%self.tickers)
        s.append("watchlist_names : %s"%self.watchlist_names   )
        s.append("base_sn : %s"%self.base_sn)
        s.append("     sn : %s"%self.base_sn)
        s.append("trading_window     : %s"%self.trading_window)
        s.append("watchlist_relation : %s"%self.watchlist_relation)
        for n in self.watchlist_names :
            s.append(str(self.watchlists[n]))
        return '\n'.join(s)

    def _get_watchlist(self, name):
        assert name in self.watchlists, "wtachlist '%s' not been created"%name
        return self.watchlists[name]

    def watchlist(self, name):
        return self._get_watchlist(name)

    def add_to_watchlist(self, name, tickers) :
        watchlist = self._get_watchlist(name)
        watchlist.add(self.sn, tickers)
        pass

    def set_watchlist(self, name, tickers) :
        watchlist = self._get_watchlist(name)
        watchlist.set(self.sn, tickers)
        pass

    def reset_watchlist(self, name, tickers = None) :
        assert name in self.watchlists, "wtachlist '%s' not been created"%name
        self.watchlists[name].reset(self.sn, tickers)

    def reset_all(self):
        for i, n in enumerate(self.watchlist_names) :
            if i == 0 :
                continue;
            self.watchlists[n].reset()

    def set_sn(self, sn) :
        assert sn >= self.sn, "set_sn sn %d must >= current sn %d"%(sn, self.sn)
        self.sn = sn
        if self.trading_window == None :
            return

        cut_sn = sn - self.trading_window
        for n in self.watchlist_names :
            self.watchlist(n).cut(cut_sn)
        #

    def get_watchlist(self, name, pos = 0):
        assert pos<=0, "pos %d ust <= 0"%pos
        s = self.watchlist(name).get(self.sn + pos)
        return sorted(s)

    def get_watchlist_until(self, name, pos = 0):
        assert pos<=0, "pos %d ust <= 0"%pos
        s = self.watchlist(name).get_until(self.sn + pos)
        return sorted(s)

    pass

if __name__ == "__main__" :
    handler = logbook.StreamHandler(sys.stdout, level=logbook.DEBUG)
    handler.formatter.format_string = '{record.time}|{record.level_name}|{record.module}|{record.func_name}|{record.lineno}|{record.message}'
    handler.push_application()

    log.info("create new watchlists")
    watchlists = WatchLists(['1', '2', '3'], ["a", 'b', 'c'], trading_window=5)
    log.info(watchlists)

    log.info("reset '1'")
    watchlists.reset_watchlist('1')
    log.info(watchlists.watchlist('1'))

    log.info("add tickers to to list '2'")
    watchlists.set_sn(1)
    watchlists.add_to_watchlist('2', 'b')
    watchlists.set_sn(1)
    watchlists.add_to_watchlist('2', 'a')
    watchlists.set_sn(2)
    watchlists.set_watchlist('2', ('b', 'c'))
    log.info("get 2, sn 1 : %s"%watchlists.get_watchlist('2',-1))
    log.info("get 2, until sn 2 : %s"%watchlists.get_watchlist_until('2', 0))
    log.info("get 2, until sn 2 : %s"%watchlists.get_watchlist_until('2'))
    log.info(watchlists)

    log.info("reset list '2'")
    watchlists.set_sn(5)
    watchlists.reset_watchlist('2', 'c')
    log.info(watchlists)

    log.info("add tickers to to list '2' outside trading window")
    watchlists.set_sn(7)
    watchlists.add_to_watchlist('2', 'a')
    log.info(watchlists)
    # log.info(watchlists.watchlist('2'))

    log.info("add tickers to to list '1'")
    watchlists.add_to_watchlist('1', 'b')
    watchlists.add_to_watchlist('1', 'a')
    watchlists.add_to_watchlist('1', 'b')
    watchlists.add_to_watchlist('1', 'c')
    log.info(watchlists)

    log.info("reset all");
    watchlists.reset_all()
    log.info(watchlists)

    log.info("done")

'''
watchlist
'''

"""
define the API for watchlists
watchlists.get(name)
watchlists.get(name, pos)  # pos <= 0
watchlists.get_until(name, pos)  # pos <= 0
watchlists.put(name, tickers)
watchlists.move(from_name, tickers, to_name)
"""


