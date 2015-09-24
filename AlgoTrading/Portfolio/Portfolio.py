# -*- coding: utf-8 -*-
u"""
Created on 2015-7-24

@author: cheng.li
"""

import pandas as pd
import numpy as np
from copy import deepcopy
from AlgoTrading.Events import OrderEvent


class Portfolio(object):

    def __init__(self, bars, events, startDate, initialCapital=100000.0):
        self.bars = bars
        self.events = events
        self.symbolList = self.bars.symbolList
        self.startDate = startDate
        self.initialCapital = initialCapital

        self.allPositions = self.constructAllPositions()
        self.currentPosition = dict((s, 0) for s in self.symbolList)

        self.allHoldings = []
        self.currentHoldings = self.constructCurrentHoldings()

    def constructAllPositions(self):
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbolList])
        d['datetime'] = self.startDate
        return [d]

    def constructAllHoldings(self):
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbolList])
        d['datetime'] = self.startDate
        d['cash'] = self.initialCapital
        d['commission'] = 0.0
        d['total'] = self.initialCapital
        return [d]

    def constructCurrentHoldings(self):
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbolList])
        d['datetime'] = self.startDate
        d['cash'] = self.initialCapital
        d['commission'] = 0.0
        d['total'] = self.initialCapital
        return d

    def updateTimeindex(self):
        latestDatetime = self.bars.getLatestBarDatetime(self.symbolList[0])
        dp = deepcopy(self.currentPosition)
        dp['date'] = latestDatetime
        self.allPositions.append(dp)

        dh = dict((s, 0) for s in self.symbolList)
        dh['datetime'] = latestDatetime
        dh['cash'] = self.currentHoldings['cash']
        dh['commission'] = self.currentHoldings['commission']
        dh['total'] = self.currentHoldings['cash']

        for s in self.symbolList:
            marketValue = self.currentPosition[s] * self.bars.getLatestBarValue(s, 'close')
            dh[s] = marketValue
            dh['total'] += marketValue

        self.allHoldings.append(dh)

    def updatePositionFromFill(self, fill):
        fillDir = fill.direction

        self.currentPosition[fill.symbol] += fillDir * fill.quantity

    def updateHoldingsFromFill(self, fill):
        self.currentHoldings[fill.symbol] += fill.fillCost
        self.currentHoldings['commission'] += fill.commission
        self.currentHoldings['cash'] -= (fill.fillCost + fill.commission)
        self.currentHoldings['total'] -= (fill.fillCost + fill.commission)

    def updateFill(self, event):
        if event.type == 'FILL':
            self.updatePositionFromFill(event)
            self.updateHoldingsFromFill(event)

    def generateNaiveOrder(self, signal):
        order = None

        symbol = signal.symbol
        direction = signal.signalType

        mktQuantity = signal.quantity
        curQuantity = self.currentPosition[symbol]
        orderType = 'MKT'

        if direction == 'LONG' and curQuantity == 0:
            order = OrderEvent(symbol, orderType, mktQuantity, 1)
        if direction == 'SHORT' and curQuantity == 0:
            order = OrderEvent(symbol, orderType, mktQuantity, -1)

        if direction == 'EXIT' and curQuantity > 0:
            order = OrderEvent(symbol, orderType, abs(curQuantity), -1)
        if direction == 'EXIT' and curQuantity < 0:
            order = OrderEvent(symbol, orderType, abs(curQuantity), 1)

        return order

    def updateSignal(self, event):
        if event.type == 'SIGNAL':
            orderEvent = self.generateNaiveOrder(event)
            self.events.put(orderEvent)

    def createEquityCurveDataframe(self):
        curve = pd.DataFrame(self.allHoldings)
        curve.set_index('datetime', inplace=True)
        curve['return'] = np.log(curve['total'] / curve['total'].shift(1))
        curve['equity_curve'] = np.exp(curve['return'].cumsum())
        self.equityCurve = curve

    def outputSummaryStats(self):
        totalReturn = self.equityCurve['equity_curve'][-1]
        returns = self.equityCurve['returns']
        pnl = self.equityCurve['equity_curve']

        #sharp_ratio = createSharpRatio(returns, perios=252 * 60 * 6.5)

