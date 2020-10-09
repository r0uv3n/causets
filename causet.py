#!/usr/bin/env python
'''
Created on 20 Jul 2020

@author: Christoph Minz
'''
from __future__ import annotations
from typing import Set, Iterable, List, Dict, Any, Tuple, Iterator, Union
import numpy as np
import itertools
from event import CausetEvent
import causet_plotting as cplt
from matplotlib import pyplot as plt, axes as plta
from builtins import int


class Causet(object):
    '''
    Causal set class to handle operations of a set of event (instances of 
    CausetEvent).
    '''

    _events: Set[CausetEvent]

    def __init__(self, eventSet: Set[CausetEvent]) -> None:
        '''
        Generates a Causet class instance from a set of event (instances of 
        CausetEvent).
        The event instances are not checked for logical consistency.
        '''
        while True:
            l: int = len(eventSet)
            eventSet = Causet.ConeOf(eventSet)
            if len(eventSet) == l:
                break
        self._events: Set[CausetEvent] = eventSet

    def __iter__(self) -> Iterable:
        return iter(self._events)

    def __repr__(self) -> str:
        return repr(self._events)

    @staticmethod
    def FromPermutation(P: List[int], labelFormat: str = None) -> 'Causet':
        '''
        Generates a causal set from the list `P` of permuted integers that 
        represent a bi-poset (also known as 2D order) that can be embedded 
        in an Alexandrov subset of 2D Minkowski spacetime.

        If the optional argument `labelFormat = None` (default) the integer 
        values are used to label the event. Use an empty string '' not to 
        label any event, or a format string, for example 'my label {.2f}'.
        '''
        eventList: List[CausetEvent] = [CausetEvent()] * len(P)
        eLabel: Any
        for i, p in enumerate(P):
            if labelFormat is None:
                eLabel = i + 1
            elif labelFormat == '':
                eLabel = None
            else:
                eLabel = labelFormat.format(i + 1)
            eventList[i] = CausetEvent(
                past={eventList[j] for j in range(i) if P[j] < p},
                label=eLabel)
        return Causet(set(eventList))

    @staticmethod
    def NewChain(n: int, labelFormat: str = None) -> 'Causet':
        '''
        Generates a causal set of `n` event in a causal chain.

        For the optional argument `labelFormat`, see `FromPermutation`.
        '''
        return Causet.FromPermutation(list(range(1, n + 1)), labelFormat)

    @staticmethod
    def NewAntichain(n: int, labelFormat: str = None) -> 'Causet':
        '''
        Generates a causal set with `n` spacelike separated event.

        For the optional argument `labelFormat`, see `FromPermutation`.
        '''
        return Causet.FromPermutation(list(range(n + 1, 1, -1)), labelFormat)

    @staticmethod
    def NewSimplex(d: int, includeCentralFace: bool = True) -> 'Causet':
        '''
        Generates a causal set that represents light travelling along the 
        faces of a d-simplex, where `d` is the space dimension.
        '''
        vertices: List[CausetEvent] = [CausetEvent(label=str(i))
                                       for i in range(1, d + 2)]
        eventSet: Set[CausetEvent] = set(vertices)
        for facenumber in range(2, d + 1):
            for face_vertices in itertools.combinations(vertices,
                                                        facenumber):
                face_label: str = '-'.join(e.Label
                                           for e in face_vertices)
                face_past: Set[CausetEvent] = set()
                for pastface_vertices in itertools.combinations(
                        face_vertices, facenumber - 1):
                    label: str = '-'.join(e.Label
                                          for e in pastface_vertices)
                    face_past.update({e for e in eventSet
                                      if e.Label == label})
                eventSet.add(CausetEvent(past=face_past, label=face_label))
        if includeCentralFace and (d > 0):
            eventSet.add(CausetEvent(past=eventSet.copy(),
                                     label='-'.join(e.Label
                                                    for e in vertices)))
        return Causet(eventSet)

    @staticmethod
    def NewFence(length: int, height: int = 1,
                 closed: bool = True) -> 'Causet':
        '''
        Generates a fence causal set of `length` (with 
        `(height + 1) * length` many event). If `closed` (default), the 
        fence needs flat spacetime of dimension 1 + 2 to be embedded, 
        otherwise it can also be embedded in flat spacetime of dimension 
        1 + 1.
        '''
        if (length < 1) or (height < 0):
            return Causet(set())
        elif length == 1:
            return Causet.NewChain(height + 1)
        else:
            loop: List[CausetEvent] = [CausetEvent(label=l)
                                       for l in range(1, length + 1)]
            eventSet: Set[CausetEvent] = set(loop)
            for h in range(1, height + 1):
                offset: int = h * length + 1
                next_loop: List[CausetEvent]
                if closed:
                    next_loop = [CausetEvent(past={loop[l - 1], loop[l]},
                                             label=l + offset)
                                 for l in range(length)]
                else:
                    next_loop = [CausetEvent(past={loop[0]}, label=offset)] \
                        + [CausetEvent(past={loop[l - 1], loop[l]},
                                       label=l + offset)
                           for l in range(1, length)]
                eventSet.update(next_loop)
                loop = next_loop
            return Causet(eventSet)

    @staticmethod
    def NewCrown(length: int = 3) -> 'Causet':
        '''
        This function is implemented for convenience.
        It redirects to `Causet.NewFence` with the default values `height=1` 
        and `closed=True`. 
        '''
        return Causet.NewFence(length, height=1, closed=True)

    @staticmethod
    def NewKROrder(n: int, rng=np.random.default_rng()):
        '''
        Returns a new Causet with 3 layers where the first and third layer 
        have `n` elements and the second layer has `2 * n` events. 
        Each event in the second layer is linked to a random number of 
        (possibly zero) events in the first layer. Each event in the third 
        layer is linked to a random number of (possibly zero) events in the 
        second layer. 
        '''
        return NotImplemented

    @staticmethod
    def FromPastMatrix(C: np.ndarray) -> 'Causet':
        '''
        Converts a logical matrix into a `Causet` object. The entry
        `C[i, j]` has to be True or 1 if the event with index j is in the 
        (link) past of event with index i.
        If the matrix has less rows than columns, empty rows are added 
        after the last row. However, if the matrix has more rows than 
        columns, a ValueError is raised. A ValueError is also raised if the 
        matrix contains causal loops.
        '''
        rowcount: int = C.shape[0]
        colcount: int = C.shape[1]
        if colcount < rowcount:
            raise ValueError('The specified matrix cannot be extended ' +
                             'to a square matrix.')
        events: np.ndarray = np.array([CausetEvent(label=i)
                                       for i in range(1, colcount + 1)])
        e: CausetEvent
        for i in range(rowcount):
            e = events[i]
            past: Set[CausetEvent] = set(events[np.where(C[i, :])[0]])
            future: Set[CausetEvent] = set(events[np.where(C[:, i])[0]])
            if (past & future) or (e in past) or (e in future):
                raise ValueError('The causet is not anti-symmetric.')
            e._prec = past
            e._succ = future
        # complete pasts and futures (if the input contains links only)
        for i in range(colcount):
            e = events[i]
            e._prec = Causet.PastOf(e._prec, includePresent=True)
            e._succ = Causet.FutureOf(e._succ, includePresent=True)
        return Causet(set(events))

    @staticmethod
    def FromFutureMatrix(C: np.ndarray) -> 'Causet':
        '''
        Returns `FromPastMatrix` of the transposed input. 
        '''
        return Causet.FromPastMatrix(C.T)

    @staticmethod
    def FromTextFile(filename: Any, isPastMatrix: bool = True,
                     delimiter: str = ',', **kwargs) -> 'Causet':
        '''
        Passes the filename and delimiter (and further keyword arguments) 
        to the `genfromtxt` function of `numpy`. The resulting logical 
        matrix is parsed with `FromPastMatrix` or `FromFutureMatrix`.
        '''
        C: np.ndarray = np.genfromtxt(filename, dtype=int,
                                      delimiter=delimiter, **kwargs)
        C = C.astype(bool)
        if isPastMatrix:
            return Causet.FromPastMatrix(C)
        else:
            return Causet.FromFutureMatrix(C)

    @staticmethod
    def merge(pastSet: Iterable, futureSet: Iterable,
              disjoint: bool = False) -> 'Causet':
        '''
        Returns a new Causet instance that joins the event sets `pastSet` 
        and futureSet.
        If not `disjoint` (default), then the event of `pastSet` are also 
        assigned to the the past of every event in `futureSet` and vice 
        versa.
        '''
        if not disjoint:  # add pastSet as past of futureSet
            for p in pastSet:
                for f in futureSet:
                    p._addToFuture(f)
                    f._addToPast(p)
        return Causet(set(pastSet) | set(futureSet))

    def add(self, eventSet: Iterable, unlink: bool = False) -> None:
        '''
        Adds all the event of the (causal) set `eventSet` 
        (Causet or Set[CausetEvent]) to this instance. 
        '''
        self._events.update(eventSet)
        if unlink:
            for e in self._events:
                e.unlink()
        if hasattr(self, '__diagram_coords'):
            delattr(self, '__diagram_coords')

    def discard(self, eventSet: Iterable, unlink: bool = False) -> None:
        '''
        Discards all the event of the (causal) set `eventSet` 
        (Causet or Set[CausetEvent]) from this instance. 
        '''
        self._events.difference_update(eventSet)
        if unlink:
            for e in self._events:
                e.unlink()
        if hasattr(self, '__diagram_coords'):
            delattr(self, '__diagram_coords')

    @staticmethod
    def len(other: 'Causet') -> int:
        '''
        Returns the number of event (set cardinality) of some Causet 
        instance.
        '''
        return len(other._events)

    @property
    def Card(self) -> int:
        '''
        Returns the number of event (set cardinality) in this instance.
        '''
        return len(self._events)

    def link(self) -> None:
        '''
        Computes the causal links between all event.
        '''
        # clear links:
        for e in self._events:
            e._lsucc = set()
        # compute links:
        for b in self._events:
            b._lprec = {a for a in b._prec if CausetEvent.isLink(a, b)}
            for a in b._lprec:
                a._lsucc.add(b)

    def unlink(self) -> None:
        '''
        Force all CausetEvent instances to reset their link memory.
        '''
        for e in self._events:
            if e.hasBeenLinked():
                e.unlink()

    def LinkCount(self, eventSet: Set[CausetEvent] = None) -> int:
        '''
        Returns the number of links between all event in `eventSet` 
        (or in this instance if `eventSet is None`).
        '''
        if eventSet is None:
            return sum([e.LinkPastCard for e in self._events])
        else:
            return sum([len(e.LinkPast & eventSet) for e in eventSet])

    def PastMatrix(self,
                   labelling: List[CausetEvent] = None) -> np.ndarray:
        '''
        Returns the logical causal past matrix such that `C[i, j]` is True 
        if the event with index j is in the past of event with index i. 
        The event are indexed by `labelling` (by default sorted by 
        causality).
        '''
        if labelling is None:
            labelling = self.sortedByCausality()
        l: int = len(labelling)
        C: np.ndarray = np.zeros((l, l), dtype=bool)
        for i, a in enumerate(labelling):
            for j, b in enumerate(labelling):
                C[i, j] = a > b
        return C

    def saveAsCSV(self, filename: str) -> None:
        '''
        Saves the causal past matrix of this object to a text file with 
        delimiter ','.
        '''
        C: np.ndarray = self.PastMatrix().astype(int)
        np.savetxt(filename, C, fmt='%.0f', delimiter=',')

    def FutureMatrix(self,
                     labelling: List[CausetEvent] = None) -> np.ndarray:
        '''
        Returns the transpose of `PastMatrix`.
        '''
        return self.PastMatrix(labelling).T

    def LinkPastMatrix(self,
                       labelling: List[CausetEvent] = None) -> np.ndarray:
        '''
        Returns the logical link past matrix such that `C[i, j]` is True if 
        the event with index j is linked in the past to event with index i. 
        The event are indexed with `labelling` (by default sorted by 
        causality).
        '''
        if labelling is None:
            labelling = self.sortedByCausality()
        l: int = len(labelling)
        C: np.ndarray = np.zeros((l, l), dtype=bool)
        for i, a in enumerate(labelling):
            for j, b in enumerate(labelling):
                C[i, j] = a.isPastLink(b)
        return C

    def LinkFutureMatrix(self,
                         labelling: List[CausetEvent] = None) -> np.ndarray:
        '''
        Returns the transpose of `LinkPastMatrix`.
        '''
        return self.FutureMatrix(labelling).T

    def find(self, label: Any) -> CausetEvent:
        '''
        Returns the first event with the given `label`. If no event 
        can be found, it raises a ValueError.
        '''
        for e in self._events:
            if e.Label == label:
                return e
        raise ValueError(f'No event with label {label} found.')

    def findAll(self, *labels: Iterable[Any]) -> Set[CausetEvent]:
        '''
        Returns a set of event with any of the given `labels`.
        '''
        return {e for e in self._events if e.Label in labels}

    def __contains__(self, other: CausetEvent) -> bool:
        return other in self._events

    def __sub__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events - set(other)

    def __rsub__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events - set(other)

    def __or__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events | set(other)

    def __ror__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events | set(other)

    def __and__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events & set(other)

    def __rand__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events & set(other)

    def __xor__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events ^ set(other)

    def __rxor__(self, other: Iterable[CausetEvent]) -> \
            Set[CausetEvent]:
        return self._events ^ set(other)

    def difference(self, other: Iterable[CausetEvent]):
        return self._events.difference(set(other))

    def intersection(self, other: Iterable[CausetEvent]):
        return self._events.intersection(set(other))

    def symmetric_difference(self, other: Iterable[CausetEvent]):
        return self._events.symmetric_difference(set(other))

    def union(self, other: Iterable[CausetEvent]):
        return self._events.union(set(other))

    def isChain(self, events: Iterable[CausetEvent] = None) -> bool:
        '''
        Tests if this instance or `event` is a causal chain.
        '''
        c: int
        if events is None:
            c = self.Card
            for e in self._events:
                if e.ConeCard != c:
                    return False
        else:
            events = set(events)
            c = len(events)
            for e in events:
                if len(e.Cone & events) != c:
                    return False
        return True

    def isPath(self, events: Iterable[CausetEvent] = None) -> bool:
        '''
        Tests if this instance or `event` is a causal path.
        '''
        if events is None:
            if self.Card == 0:
                return False
            else:
                return self.isChain()
        else:
            events = set(events)
            if len(events) <= 1:
                return len(events) == 1
            extremal: int = 0
            for e in events:
                e_linkcount: int = len(e.LinkCone & events)
                if (e_linkcount < 1) or (e_linkcount > 2):
                    return False
                elif e_linkcount == 1:
                    extremal += 1
                    if extremal > 2:
                        return False
        return True

    def isAntichain(self, events: Iterable[CausetEvent] = None) -> bool:
        '''
        Tests if this instance or `event` is a causal anti-chain.
        '''
        if events is None:
            for e in self._events:
                if e.ConeCard != 1:
                    return False
        else:
            events = set(events)
            for e in events:
                if len(e.Cone & events) != 1:
                    return False
        return True

    @staticmethod
    def _Permutation_Coords(P: List[int], radius: float) -> np.ndarray:
        '''
        Returns a matrix of (t, x) coordinates with `len(P)` rows, a 
        pair of coordinates for each element in the permutation integer 
        list (integers from 1 to `len(P)`).
        '''
        count: int = len(P)
        coords: np.ndarray = np.empty((count, 2))
        if count > 0:
            cellscale: float = radius / float(count)
            for i, p in enumerate(P):
                crd_u: float = (p - 0.5) * cellscale
                crd_v: float = (i + 0.5) * cellscale
                coords[i, 0] = crd_u + crd_v - radius
                coords[i, 1] = crd_u - crd_v
        return coords

    @property
    def PastInf(self) -> Set[CausetEvent]:
        '''
        Returns the set of event without any past event (past infinity).
        '''
        return {e for e in self._events if e.PastCard == 0}

    @property
    def FutureInf(self) -> Set[CausetEvent]:
        '''
        Returns the set of event without any future event (future 
        infinity).
        '''
        return {e for e in self._events if e.FutureCard == 0}

    @property
    def PastInfCard(self) -> int:
        '''
        Returns the number of event without any past event (past infinity).
        '''
        return sum(1 for e in self._events if e.PastCard == 0)

    @property
    def FutureInfCard(self) -> int:
        '''
        Returns the number of event without any future event (future 
        infinity).
        '''
        return sum(1 for e in self._events if e.FutureCard == 0)

    @staticmethod
    def PastInfOf(eventSet: Set[CausetEvent]) -> Set[CausetEvent]:
        '''
        Returns a subset of event without any past event (past 
        infinity) in `eventSet`.
        '''
        return {e for e in eventSet if not (e.Past & eventSet)}

    @staticmethod
    def FutureInfOf(eventSet: Set[CausetEvent]) -> Set[CausetEvent]:
        '''
        Returns a subset of event without any future event (future 
        infinity) in `eventSet`.
        '''
        return {e for e in eventSet if not (e.Future & eventSet)}

    @staticmethod
    def PastInfCardOf(eventSet: Set[CausetEvent]) -> int:
        '''
        Returns the number of event without any past event (past 
        infinity) in `eventSet`.
        '''
        return sum(1 for e in eventSet if not (e.Past & eventSet))

    @staticmethod
    def FutureInfCardOf(eventSet: Set[CausetEvent]) -> int:
        '''
        Returns the number of event without any future event (future 
        infinity) in `eventSet`.
        '''
        return sum(1 for e in eventSet if not (e.Future & eventSet))

    @staticmethod
    def PastOf(eventSet: Set[CausetEvent],
               includePresent: bool = False,
               intersect: bool = False) -> Set[CausetEvent]:
        '''
        Returns the set of event that are in the past of `eventSet`.
        '''
        newEventSet: Set[CausetEvent] = set()
        if includePresent and intersect:
            for e in eventSet:
                newEventSet &= e.PresentOrPast
        elif intersect:
            for e in eventSet:
                newEventSet &= e.Past
        else:
            for e in eventSet:
                newEventSet |= e.Past
            if includePresent:
                newEventSet |= eventSet
        return newEventSet

    @staticmethod
    def FutureOf(eventSet: Set[CausetEvent],
                 includePresent: bool = False,
                 intersect: bool = False) -> Set[CausetEvent]:
        '''
        Returns the set of event that are in the future of `eventSet`.
        '''
        newEventSet: Set[CausetEvent] = set()
        if includePresent and intersect:
            for e in eventSet:
                newEventSet &= e.PresentOrFuture
        elif intersect:
            for e in eventSet:
                newEventSet &= e.Future
        else:
            for e in eventSet:
                newEventSet |= e.Future
            if includePresent:
                newEventSet |= eventSet
        return newEventSet

    @staticmethod
    def ConeOf(eventSet: Set[CausetEvent],
               includePresent: bool = True,
               intersect: bool = False) -> Set[CausetEvent]:
        '''
        Returns the set of event that are in the cone of `eventSet`.
        '''
        newEventSet: Set[CausetEvent] = set()
        if includePresent and intersect:
            for e in eventSet:
                newEventSet &= e.Cone
        elif intersect:
            for e in eventSet:
                newEventSet &= (e.Past | e.Future)
        else:
            for e in eventSet:
                newEventSet |= e.Past | e.Future
            if includePresent:
                newEventSet |= eventSet
        return newEventSet

    def SpacelikeTo(self, eventSet: Set[CausetEvent]) -> Set[CausetEvent]:
        '''
        Returns the set of event that are spacelike separated to 
        `eventSet`.
        '''
        return self._events - self.ConeOf(eventSet, includePresent=True)

    @staticmethod
    def Interval(a: CausetEvent, b: CausetEvent,
                 includeBoundary: bool = True) -> Set[CausetEvent]:
        '''
        Returns the causal interval (Alexandrov set) between event a and b 
        or an empty set if not `a <= b`.
        If `includeBoundary == True` (default), the event a and b are 
        included in the interval.
        '''
        if not a <= b:
            return set()
        elif a == b:
            return {a}
        elif includeBoundary:
            return a.PresentOrFuture & b.PresentOrPast
        else:
            return a.Future & b.Past

    @staticmethod
    def IntervalCard(a: CausetEvent, b: CausetEvent,
                     includeBoundary: bool = True) -> int:
        '''
        Returns the cardinality of the causal interval (Alexandrov set) 
        between event a and b or 0 if not `a <= b`.
        If `includeBoundary == True` (default), the event a and b are 
        included in the interval.
        '''
        if not a <= b:
            return 0
        elif a == b:
            return 1
        else:
            return len(a.Future & b.Past) + 2 * int(includeBoundary)

    @staticmethod
    def PerimetralEvents(a: CausetEvent, b: CausetEvent) -> Set[CausetEvent]:
        '''
        Returns the event that are linked between event a and b, with a in 
        the past and b in the future, or an empty set if there are no such 
        event.
        '''
        if not (a < b):
            return set()
        else:
            return a.LinkFuture & b.LinkPast

    @staticmethod
    def PerimetralEventCount(a: CausetEvent, b: CausetEvent) -> int:
        '''
        Returns the number of event that are linked between event a and b, 
        with a in the past and b in the future.
        '''
        if not (a < b):
            return 0
        else:
            return len(a.LinkFuture & b.LinkPast)

    @staticmethod
    def InternalEvents(a: CausetEvent, b: CausetEvent) -> Set[CausetEvent]:
        '''
        Returns the event that are not in a rank 2 path from event a to 
        event b, or an empty set if there are no such event.
        '''
        if not (a < b):
            return set()
        else:
            return (a.Future & b.Past) - \
                Causet.PerimetralEvents(a, b)

    @staticmethod
    def InternalEventCount(a: CausetEvent, b: CausetEvent) -> int:
        '''
        Returns the number of event that are not in a rank 2 path from 
        event a to event b.
        '''
        if not (a < b):
            return 0
        else:
            return len(a.Future & b.Past) - \
                Causet.PerimetralEventCount(a, b)

    def CentralAntichain(self, e: CausetEvent = None) -> Set[CausetEvent]:
        '''
        Returns the set of event that forms a maximal antichain with event 
        that have a similar past and future cardinality (like event e if 
        specified).
        '''
        # Compute the absolute sizes of past minus future lightcones:
        diff: int
        if e is None:
            diff = 0
        else:
            diff = e.PastCard - e.FutureCard
        sizeList: np.ndarray = np.array([
            abs(e.PastCard - e.FutureCard - diff) for e in self._events])
        sizes = np.unique(sizeList)
        # Find maximal antichain of event that minimises the sizes:
        eventSet: Set[CausetEvent] = set()
        for size in sizes:
            for i, e in enumerate(self._events):
                if (sizeList[i] == size) and not (e.Cone & eventSet):
                    eventSet.add(e)
        return eventSet

    @staticmethod
    def Layers(eventSet: Set[CausetEvent],
               first: int, last: int = None) -> Set[CausetEvent]:
        '''
        Returns the layers of `eventSet` with layer number from `first` to 
        `last`. If `last` is None (default), `last` is set to `first`.
        Past layers have a negative layer number, 0 stands for the present 
        layer (eventSet itself), and future layer have a positive layer 
        number.
        '''
        if last is None:
            last = first
        if (len(eventSet) == 0) or (first > last):
            return set()
        newEventSet: Set[CausetEvent] = set()
        n: int
        if first <= 0:
            _last = min(0, last)
            for a in Causet.PastOf(eventSet, includePresent=True):
                setB: Set[CausetEvent] = a.Future & eventSet
                if setB:
                    n = -(max(Causet.IntervalCard(a, b)
                              for b in setB) - 1)
                else:
                    n = 0
                if (n >= first) and (n <= _last):
                    newEventSet.add(a)
        if last > 0:
            _first = max(first, 0)
            for b in Causet.FutureOf(eventSet, includePresent=True):
                setA: Set[CausetEvent] = b.Past & eventSet
                if setA:
                    n = max(Causet.IntervalCard(a, b)
                            for a in setA) - 1
                else:
                    n = 0
                if (n >= _first) and (n <= last):
                    newEventSet.add(b)
        return newEventSet

    @staticmethod
    def LayerNumbers(eventList: List[CausetEvent],
                     reverse: bool = False) -> List[int]:
        '''
        Returns a list of layer numbers for the list of event `eventList`. 
        If not `reverse` (default), the layer numbers are non-negative and 
        increasing from the past infinity of `eventList`. If reverse, the 
        layer numbers are non-positive and decreasing from the future 
        infinity of `eventList`. 
        '''
        eventSet: Set[CausetEvent] = set(eventList)
        if len(eventSet) == 0:
            return []
        lnums: List[int] = [0] * len(eventList)
        if reverse:
            for i, a in enumerate(eventList):
                setB: Set[CausetEvent] = a.Future & eventSet
                if setB:
                    lnums[i] = -(max(Causet.IntervalCard(a, b)
                                     for b in (a.Future & eventSet)) - 1)
        else:
            for i, b in enumerate(eventList):
                setA: Set[CausetEvent] = b.Past & eventSet
                if setA:
                    lnums[i] = max(Causet.IntervalCard(a, b)
                                   for a in (b.Past & eventSet)) - 1
        return lnums

    @staticmethod
    def Ranks(eventSet: Set[CausetEvent],
              first: int, last: int = None) -> Set[CausetEvent]:
        '''
        Returns the ranks of `eventSet` with rank number from `first` to 
        `last`. If `last` is None (default), `last` is set to `first`.
        Past ranks have a negative rank number, 0 stands for the present 
        rank (`eventSet` itself), and future ranks have a positive rank 
        number.
        '''
        if last is None:
            last = first
        if (len(eventSet) == 0) or (first > last):
            return set()
        newEventSet: Set[CausetEvent] = set()
        if first <= 0:
            _last = min(0, last)
            for a in Causet.PastOf(eventSet, includePresent=True):
                setB: Set[CausetEvent] = a.Future & eventSet
                if setB:
                    n = -max(int(a.Rank(b)) for b in setB)
                else:
                    n = 0
                if (n >= first) and (n <= _last):
                    newEventSet.add(a)
        if last > 0:
            _first = max(first, 0)
            for b in Causet.FutureOf(eventSet, includePresent=True):
                setA: Set[CausetEvent] = b.Past & eventSet
                if setA:
                    n = max(int(a.Rank(b)) for a in setA)
                else:
                    n = 0
                if (n >= _first) and (n <= last):
                    newEventSet.add(b)
        return newEventSet

    @staticmethod
    def RankNumbers(eventList: List[CausetEvent],
                    reverse: bool = False) -> List[int]:
        '''
        Returns a list of rank numbers for the list of event `eventList`. 
        If not `reverse` (default), the rank numbers are non-negative and 
        increasing from the past infinity of `eventList`. If reverse, the 
        rank numbers are non-positive and decreasing from the future 
        infinity of `eventList`. 
        '''
        eventSet: Set[CausetEvent] = set(eventList)
        if len(eventSet) == 0:
            return []
        lnums: List[int] = [0] * len(eventList)
        if reverse:
            for i, a in enumerate(eventList):
                setB: Set[CausetEvent] = a.Future & eventSet
                if setB:
                    lnums[i] = -max(int(a.Rank(b)) for b in setB)
        else:
            for i, b in enumerate(eventList):
                setA: Set[CausetEvent] = b.Past & eventSet
                if setA:
                    lnums[i] = max(int(a.Rank(b)) for a in setA)
        return lnums

    @staticmethod
    def Paths(a: CausetEvent, b: CausetEvent,
              length: Union[str, int, List[int]] = 'any') -> \
            Iterator[List[CausetEvent]]:
        '''
        Iterates over all paths (list of CausetEvent) from event a to 
        event b that have a specific `length`. As optional argument, the 
        `length` can be specified with the following meanings:
        'any': paths of any `length` (default)
        'min': paths of minimal `length`
        'max' or 'timegeo': paths of maximal `length` (timelike geodesics)
        A single int value sets a fixed `length`.
        A list of two int values sets an accepted minimum and maximum of 
        the `length`.
        '''
        find_min: bool = False
        find_max: bool = False
        min_len: int = 0
        max_len: int = -1
        if isinstance(length, str):
            find_min = length == 'min'
            find_max = length in {'max', 'timegeo'}
        elif isinstance(length, int):
            min_len, max_len = length, length
        elif isinstance(length, list):
            min_len, max_len = length[0], length[-1]
        else:
            raise ValueError(
                'The optional argument \'length\' must be of ' +
                'type str, int or List[int].')
        # handle trivial paths:
        if not (a <= b):
            return
        elif a is b:
            if (min_len <= 1) and ((1 <= max_len) or (max_len == -1)):
                yield [a]
        elif a.isFutureLink(b):
            if (min_len <= 2) and ((2 <= max_len) or (max_len == -1)):
                yield [a, b]
        elif (3 <= max_len) or (max_len == -1):
            # handle longer paths:
            b_linked: Set[CausetEvent] = a.Future & b.LinkPast

            def Paths_find(path_a: List[CausetEvent], a: CausetEvent,
                           l: int) -> Iterator[List[CausetEvent]]:
                nonlocal min_len, max_len
                a_linked: Set[CausetEvent] = a.LinkFuture & b.Past
                perimetral: Set[CausetEvent] = a_linked & b_linked
                internal: Set[CausetEvent] = a_linked - perimetral
                perimetral_count: int = len(perimetral)
                internal_count: int = len(internal)
                # path step along perimetral event:
                if (min_len <= l) and (perimetral_count > 0) and \
                        (not find_max or (internal_count == 0)):
                    for e in perimetral:
                        yield path_a + [e, b]
                    if find_min:
                        if (l <= max_len) or (max_len == -1):
                            max_len = l  # local minimum
                        return
                # path step along internal event:
                if find_max:
                    min_len = max(min_len, l)  # local maximum
                if l == max_len:
                    return
                l += 1
                for e in internal:
                    for p in Paths_find(path_a + [e], e, l):
                        yield p

            if find_min or find_max:
                # first extract all paths and find minimal/maximal length:
                P: List[List[CausetEvent]] = list(Paths_find([a], a, 3))
                if find_min:
                    for p in P:
                        if len(p) == max_len:
                            yield p
                else:
                    for p in P:
                        if len(p) == min_len:
                            yield p
            else:  # iterate over all paths in the given range:
                for p in Paths_find([a], a, 3):
                    yield p

    def SmallestIntervalCard(self, a: CausetEvent, b: CausetEvent,
                             searching: Set[CausetEvent] = None,
                             intersecting: Set[CausetEvent] = None) -> int:
        '''
        For `a <= b`, it returns the cardinality of the interval from a to b. 

        For `a > b`, it returns the cardinality of the interval from b to a. 

        When a is spacelike to b, it returns the smallest cardinality among 
        the intervals from one event in the past of a and b to one event in 
        the future of a and b.

        The optional argument 'searching' provides the set of event of start 
        and end points of any causal interval.
        The optional argument 'intersecting' provides the set of event that 
        is intersected with the interval before the cardinality is computed.
        Default for both is the entire causet.

        If either no common past event or no common future event is in the 
        'searching' set (or the entire causet), the entire past or future is 
        considered, respectively. If neither a common past event nor a common 
        future event exist, 0 is returned.
        '''
        if a > b:
            a, b = b, a
        if a <= b:
            if (searching is None) or \
                    (a in searching and b in searching):
                return self.IntervalCard(a, b) if intersecting is None \
                    else len(self.Interval(a, b) & intersecting)
            elif a in searching:  # but not b in searching
                return a.FutureCard if intersecting is None \
                    else len(a.Future & intersecting)
            elif b in searching:  # but not a in searching
                return b.PastCard if intersecting is None \
                    else len(b.Past & intersecting)
        if searching is None:
            searching = self._events
        pastIntersect = a.Past & b.Past & searching
        futureIntersect = a.Future & b.Future & searching
        if not pastIntersect and not futureIntersect:
            return 0
        elif not pastIntersect:  # but futureIntersect
            return min(e.PastCard for e in futureIntersect) \
                if intersecting is None \
                else min(len(e.Past & intersecting) for e in futureIntersect)
        elif not futureIntersect:  # but pastIntersect
            return min(e.FutureCard for e in pastIntersect) \
                if intersecting is None \
                else min(len(e.Future & intersecting) for e in pastIntersect)
        elif intersecting is None:  # pastIntersect and futureIntersect
            return min(self.IntervalCard(e_p, e_f)
                       for e_p in pastIntersect
                       for e_f in futureIntersect)
        else:  # pastIntersect and futureIntersect
            return min(len(self.Interval(e_p, e_f) & intersecting)
                       for e_p in pastIntersect
                       for e_f in futureIntersect)

    def DistanceMatrix(self, antichain: Union[List[CausetEvent],
                                              Tuple[CausetEvent, ...],
                                              np.ndarray],
                       counting: str = 'ziczac',
                       recursive: bool = True) -> np.ndarray:
        '''
        Computes a symmetric matrix (ndarray of int) from counting the 
        distances between every pair of event from the `antichain`. The 
        rows and columns are labelled by the index of the list `antichain`.

        As optional argument `counting` specifies the method 
        how the distances are computed:
        'ziczac' (default) uses the number of alternating along a past and 
        a future link - one ziczac counts as 1.
        'intersection' uses the number of all event along `antichain` that 
        intersect the smallest intervals (see also 'SmallestIntervalCard').

        The optional argument `recursive` specifies if the distances are 
        recursively added (default) or the distance computation breaks 
        after the first iteration. 
        '''
        is_counting_ziczac: bool = counting == 'ziczac'
        if not is_counting_ziczac and (counting != 'intersection'):
            raise ValueError(f'Counting method \'{counting}\' is not ' +
                             'supported.\n' +
                             'Use \'ziczac\' or \'intersection\'.')
        l: int = len(antichain)
        D: np.ndarray = np.zeros((l, l), dtype=int)
        ac_set: Set[CausetEvent] = set(antichain)
        slice_set: Set[CausetEvent] = ac_set
        thickerslice_set = self.Layers(slice_set, -1, 1)
        d: int
        while len(slice_set) < len(thickerslice_set):
            slice_set = thickerslice_set
            for i, j in itertools.combinations(range(l), 2):
                if D[i, j] < 1:
                    d = self.SmallestIntervalCard(
                        antichain[i], antichain[j],
                        searching=slice_set, intersecting=ac_set) - 1
                    if is_counting_ziczac:
                        d = min(1, d)
                    D[i, j], D[j, i] = d, d
            if not recursive:
                break
            disconnected_count: int = np.sum(D < 0)
            for k in range(1, l):
                for i in range(l):
                    i_disjoint: np.ndarray = D[i, :] < 0
                    i_connected: np.ndarray = D[i, :] == k
                    for j in np.where(i_disjoint)[0]:
                        j_connected: np.ndarray = D[j, :] == 1
                        ij_connected: np.ndarray = i_connected & j_connected
                        if np.sum(ij_connected) > 0:
                            ij_dist = D[i, :] + D[j, :]
                            d = min(ij_dist[ij_connected])
                            D[i, j], D[j, i] = d, d
                            disconnected_count -= 2
                            if disconnected_count == 0:
                                return D
            thickerslice_set = self.Layers(slice_set, -1, 1)
        return D

    def Antipaths(self, a: CausetEvent, b: CausetEvent,
                  along: Iterable[CausetEvent],
                  distances: np.ndarray = None) -> \
            Iterator[List[CausetEvent]]:
        '''
        Iterates over all shortest spacelike paths (list of CausetEvent) 
        from event a to event b that are part of the (maximal) antichain 
        `along`. 
        As optional argument, the distances matrix can be specified if it 
        has already been computed.
        '''
        if a is b and a in along:
            yield [a]
        if not (a.isSpacelikeTo(b) and a in along and b in along):
            return
        antichainList: List[CausetEvent] = list(along)
        a_idx: int = antichainList.index(a)
        b_idx: int = antichainList.index(b)
        D: np.ndarray = distances if distances is not None \
            else self.DistanceMatrix(antichainList, recursive=True)
        if D[a_idx, b_idx] == -1:
            return

        def Antipaths_find(e_idx: int) -> Iterator[List[CausetEvent]]:
            if D[e_idx, b_idx] == 1:
                yield [antichainList[e_idx], b]
            else:
                a_neighbours_sel: np.ndarray = \
                    D[e_idx, :] == np.min(D[e_idx, D[e_idx, :] > 0])
                b_closer_sel: np.ndarray = \
                    D[b_idx, :] == np.min(D[b_idx, a_neighbours_sel])
                for e2_idx in np.where(a_neighbours_sel & b_closer_sel)[0]:
                    for ap in Antipaths_find(e2_idx):
                        yield [antichainList[e_idx]] + ap

        for ap in Antipaths_find(a_idx):
            yield ap

    def disjoint(self, eventSet: Set[CausetEvent] = None) -> \
            List[Set[CausetEvent]]:
        '''
        Converts the `eventSet` (or the entire causet if `eventSet == 
        None`) to a list of subsets such that each subset contains event 
        that are spacelike separated to all event from any other subset 
        in the list, but all event of any subset are linked to all other 
        event in this subset. It is a list of disjoint sets. 
        '''
        remaining: Set[CausetEvent]
        if eventSet is None:
            remaining = self._events.copy()
        else:
            remaining = eventSet.copy()
        disjointSubsets: List[Set[CausetEvent]] = []
        disjointSubset: Set[CausetEvent] = set()
        while remaining:
            disjointSubset = {next(iter(remaining))}
            pre_len: int = 0
            this_len: int = len(disjointSubset)
            while pre_len < this_len:
                pre_len = this_len
                disjointSubset = self.ConeOf(disjointSubset) & remaining
                this_len = len(disjointSubset)
            disjointSubsets.append(disjointSubset)
            remaining.difference_update(disjointSubset)
        return disjointSubsets

    def isDisjoint(self, eventSet: Set[CausetEvent] = None) -> bool:
        '''
        Returns True if the `eventSet` (or the entire causet if `eventSet 
        == None`) consists of disjoint pieces, otherwise False.
        '''
        return len(self.disjoint(eventSet)) > 1

    def sortedByLabels(self, eventSet: Set[CausetEvent] = None,
                       reverse: bool = False) -> List[CausetEvent]:
        '''
        Returns the causet event `eventSet` (if None than the entire 
        causet) as a list sorted ascending (default) or descending by 
        their labels.
        '''
        if eventSet is None:
            eventSet = self._events
        unsortedList: List[CausetEvent] = list(eventSet)
        sortedIndex: np.ndarray = \
            np.argsort([e.Label for e in unsortedList])
        sortedList: List[CausetEvent] = \
            [unsortedList[i] for i in sortedIndex]
        if reverse:
            sortedList.reverse()
        return sortedList

    def sortedByCausality(self, eventSet: Set[CausetEvent] = None,
                          reverse: bool = False) -> List[CausetEvent]:
        '''
        Returns the causet event `eventSet` (if None than the entire 
        causet) as a list sorted ascending (default) or descending by 
        their causal relations.
        '''
        if eventSet is None:
            eventSet = self._events
        eList: List[CausetEvent] = self.sortedByLabels(eventSet, reverse=True)
        c: int = len(eList)
        for i in range(c):
            for j in range(i):
                if eList[i] < eList[j]:
                    eList[i], eList[j] = eList[j], eList[i]
        if reverse:
            eList.reverse()
        return eList

    def layered(self, eventSet: Set[CausetEvent] = None,
                reverse: bool = False) -> List[Set[CausetEvent]]:
        '''
        Returns the causet event in a list of sets that represent 
        layers starting from the past infinity if not `reverse` (default) or 
        starting from the future infinity if `reverse`. 
        '''
        if eventSet is None:
            eventSet = self._events
        layer_step: int = -1 if reverse else 1
        layer: Set[CausetEvent]
        if reverse:
            layer = self.FutureInfOf(eventSet)
        else:
            layer = self.PastInfOf(eventSet)
        layeredList: List[Set[CausetEvent]] = []
        while layer:
            layeredList.append(layer)
            layer = self.Layers(layer, layer_step) & eventSet
        return layeredList

    def AntichainPermutations(self, antichain: Set[CausetEvent],
                              orientationLayer: List[CausetEvent] = None,
                              includeLocalSymmetries: bool = False,
                              includeGlobalSymmetry: bool = False) -> \
            Iterator[List[CausetEvent]]:
        ac_list: List[CausetEvent] = list(antichain)
        D: np.ndarray = self.DistanceMatrix(ac_list, counting='intersection',
                                            recursive=True)
        for i, j in zip(*np.where(D == np.max(D))):
            if includeGlobalSymmetry or (i < j):
                ac_perm: List[CausetEvent]
                for p in self.Antipaths(ac_list[i], ac_list[j],
                                        along=ac_list, distances=D):
                    ac_perm = p
                    ac_perm
                yield ac_perm

    def AntichainPermutations_old(self, eventSet: Set[CausetEvent],
                                  pastLayer: Tuple[CausetEvent, ...] = ()) -> \
            Iterator[Tuple[CausetEvent, ...]]:
        '''
        Returns an iterator that yields all possible permutations of the 
        antichain given by `eventSet`.
        '''
        c: int = len(eventSet)
        events: np.ndarray = np.array(
            self.sortedByLabels(eventSet), dtype=CausetEvent)
        # create distance matrix:
        D: np.ndarray = np.zeros((c, c), dtype=int)
        for i in range(c):
            for j in range(i + 1, c):
                dist: int = self.SmallestIntervalCard(
                    events[i], events[j], eventSet) - 1
                if dist < 0:
                    dist = c
                D[i, j], D[j, i] = dist, dist
        print(D)

        # create index permutation extender:
        def __extend(subP: np.ndarray) -> Iterator[np.ndarray]:
            while subP.size < c:
                # find next closest index p:
                sel: np.ndarray = np.ones((c,), dtype=bool)
                sel[subP] = False
                p: int
                minvalue: int = c
                for i in np.where(sel)[0]:
                    m: int = min(D[subP, i])
                    if (m < minvalue) or (m == c):
                        p, minvalue = i, m
                # find sub-indices where to insert p:
                min_indices: np.ndarray
                if (minvalue == c) and (D[subP[0], p] == c):
                    min_indices = np.array([subP.size - 1])
                elif (minvalue == c) and (D[subP[-1], p] == c):
                    min_indices = np.array([0])
                else:
                    min_indices = np.where(D[subP, p] == minvalue)[0]
                p_indices: np.ndarray = np.array([], dtype=int)
                for offset in [0, 1]:  # try left and then right appending
                    for i in (min_indices + offset):  # insert index
                        if i in p_indices:
                            continue
                        p_has_past_in_layer: bool = False
                        for e in (pastLayer if offset == 0 else reversed(pastLayer)):
                            if e < events[p]:
                                p_has_past_in_layer = True
                            if e < events[subP[i]]:
                                if p_has_past_in_layer:
                                    p_indices = np.append(p_indices, i)
                                break
                        else:
                            if (subP.size == 1) and (offset == 1):
                                p_indices = np.append(p_indices, i)
                            elif ((i - 1 < 0) or D[subP[i - 1], p] < c) and \
                                    ((i >= subP.size) or D[subP[i], p] < c):
                                p_indices = np.append(p_indices, i)
                # insert p into subP at any of p_indices:
                self._print_eventlist(events[subP])
                if p_indices.size > 1:
                    for i in p_indices:
                        try:
                            yield np.insert(subP, i, p)
                        except IndexError:
                            yield np.append(subP, p)
                    break
                else:
                    # There is only one insertion index.
                    # No need for branching the output with `yield` and
                    # the loop continues.
                    try:
                        subP = np.insert(subP, p_indices, p)
                    except IndexError:
                        subP = np.append(subP, p)
            else:
                yield subP

        # initialise start of index permutations:
        P: np.ndarray = np.array([], dtype=int)
        P_extension_steps: List[np.ndarray] = [P]
        cone_card: int = -1
        for i, e in enumerate(events):
            e_cone_card: int = e.ConeCard
            if e_cone_card > cone_card:
                P = np.array([i])
                cone_card = e_cone_card
        # extend and iterate through index permutations:
        P_extensions: List[Iterator[np.ndarray]] = [iter([P])]
        while P_extensions:
            try:
                P = next(P_extensions[-1])
            except StopIteration:
                P_extensions.pop()
                P_extension_steps.pop()
                continue
            if np.size(P) == c:
                self._print_eventlist(tuple(events[P]))
                yield tuple(events[P])
            else:
                P_extension_steps.append(P)
                P_extensions.append(__extend(P))

    @staticmethod
    def _print_eventlist(el: Iterable[CausetEvent]) -> None:
        '''
        Private, debug method: Print an iterable of CausetEvent as a 
        short line console output.
        '''
        print(', '.join(str(e) for e in el))

    @staticmethod
    def _print_eventlists(ell: Iterable[Iterable[CausetEvent]]) -> None:
        '''
        Private, debug method: Print an iterable of an iterable of 
        CausetEvent as a short line console output.
        '''
        print('| '.join(', '.join(str(e) for e in el) for el in ell))

    def layeredPermutations(self, eventSet: Set[CausetEvent] = None) -> \
            Iterator[List[List[CausetEvent]]]:
        '''
        Returns an iterator that yields all possible permutations of all 
        layers of the set `eventSet`.
        '''
        if eventSet is None:
            eventSet = self._events
        layer_sets: List[Set[CausetEvent]] = self.layered(eventSet)
        layer_count: int = len(layer_sets)
        layer_iterators: List[Iterator[List[CausetEvent]]] = \
            [iter([[CausetEvent()]])] * layer_count
        layers_perm: List[List[CausetEvent]] = [[]] * layer_count
        # initialise:
        for l, layer_set in enumerate(layer_sets):
            layer_iterators[l] = self.AntichainPermutations(
                layer_set, layers_perm[0])
            layers_perm[l] = next(layer_iterators[l])
        # iterate:
        is_exhausted: bool = False
        while not is_exhausted:
            yield layers_perm
            for l in range(layer_count - 1, -1, -1):
                try:
                    layers_perm[l] = next(layer_iterators[l])
                except StopIteration:
                    is_exhausted = (l == 0)
                else:
                    break
            if not is_exhausted:
                for k in range(l + 1, layer_count):
                    layer_iterators[k] = self.AntichainPermutations(
                        layer_sets[k], layers_perm[0])
                    layers_perm[k] = next(layer_iterators[k])

    def permuted(self, eventSet: Set[CausetEvent] = None,
                 maxIterations: int = 100000) -> \
            Tuple[List[CausetEvent], List[int]]:
        '''
        Searches for a permutation of integers from 1 to len(eventSet) + 1 
        such that the permutation determines a causet that is a 2D projected 
        version of this instance. This function provides can be used to 
        obtain a `flattened` causet to draw a Hasse diagram.
        If eventSet = None (default), all causet event are included.

        The optional parameter `maxIterations` sets the limit of iterations 
        in the optimisation. If this value is reaches without finding any 
        valid permutation, the function raises a ValueError.
        '''
        if eventSet is None:
            eventSet = self._events
        eventSet_len = len(eventSet)
        # Reserve buffer for result:
        L: List[CausetEvent] = []   # permutation of event
        P: List[int] = []           # integers to generate coordinates
        extension_degree: int = -1  # number of extended causal relations
        iteration: int = 0
        for layers in self.layeredPermutations(eventSet):
            iteration += 1
            if iteration > maxIterations:
                if extension_degree == -1:
                    raise ValueError('Function \'permuted\' failed with ' +
                                     f'{maxIterations} permutations. ' +
                                     'Try to increase \'maxIterations\'.')
                break
            L_this = [CausetEvent()] * eventSet_len
            P_this = [0] * eventSet_len
            i_first: int
            i_last: int
            # Extend the future of each event by those event in future
            # layers that are between two other future event in the layers:
            layers_len = len(layers)
            ext_futures: Dict[CausetEvent, Set[CausetEvent]] = {}
            for l in range(layers_len - 1, -1, -1):
                layer = layers[l]
                for a in layer:
                    ext_future: Set[CausetEvent] = a.Future & eventSet
                    for m in range(l, layers_len):
                        future_layer: List[CausetEvent] = layers[m]
                        i_first = 0
                        i_last = -1
                        for i, b in enumerate(future_layer):
                            if a < b:
                                if i_first > i_last:
                                    i_first = i
                                i_last = i
                        for i, b in enumerate(future_layer):
                            if i_first <= i <= i_last:
                                ext_future.add(b)
                                ext_future.update(ext_futures[b])
                    ext_futures[a] = ext_future
            # Extend the past of each event by those event in past
            # layers that are between two other past event in the layers:
            ext_pasts: Dict[CausetEvent, Set[CausetEvent]] = {}
            try:
                for l, layer in enumerate(layers):
                    right: Set[CausetEvent] = set()
                    for j, b in enumerate(layer):
                        ext_past: Set[CausetEvent] = b.Past & eventSet
                        for k in range(l - 1, -1, -1):
                            past_layer: List[CausetEvent] = layers[k]
                            i_first = 0
                            i_last = -1
                            for i, a in enumerate(past_layer):
                                if a < b:
                                    if i_first > i_last:
                                        i_first = i
                                    i_last = i
                            for i, a in enumerate(past_layer):
                                if i_first <= i <= i_last:
                                    ext_past.add(a)
                                    ext_past.update(ext_pasts[a])
                            if (j == 0) and (i_first > 0):
                                # initialise right region for
                                # right-most event in `layer`:
                                for a in past_layer[:i_first]:
                                    right.add(a)
                                    right.update(ext_futures[a])
                        ext_pasts[b] = ext_past
                    # Find u and v coordinates with the cardinalities of
                    # the event in the past, right and left regions:
                    for e in layer:
                        ext_cone: Set[CausetEvent] = \
                            ext_pasts[e] | ext_futures[e]
                        ext_cone.add(e)
                        right.difference_update(ext_cone)
                        left: Set[CausetEvent] = eventSet.copy()
                        left.difference_update(right)
                        left.difference_update(ext_cone)
                        past_card: int = len(ext_pasts[e])
                        u: int = past_card + len(left) + 1
                        v: int = past_card + len(right)
                        L_this[v] = e  # might raise IndexError if v too large
                        P_this[v] = u
                        right.update(ext_cone)
                if 0 in P_this:
                    raise IndexError
            except IndexError:
                continue
            else:
                # Minimise number of extended causal relations:
                extended_causals: int = sum(len(ext_futures[e] - e.Future)
                                            for e in eventSet)
                if (extension_degree == -1) or \
                        (extended_causals < extension_degree):
                    L = L_this
                    P = P_this
                    extension_degree = extended_causals
                if extension_degree == 0:
                    break
                else:
                    continue
        return (L, P)

    def plotDiagram(self, eventSet: Set[CausetEvent] = None,
                    ax: plta.Axes=None, **kwargs) -> Dict[str, Any]:
        '''
        Plots this instance as Hasse diagram and returns a dictionary of 
        pointers to the plotted objects with entries for `event` and 
        `links`.
        The plot axes object `ax` defaults to `matplotlib.gca()`.
        Further plot options are listed in 
        `causet_plotting.plot_parameters`.
        '''
        if (not hasattr(self, '__diagram_coords')) or \
                (self.__diagram_coords is None) or \
                (eventSet is not None):
            self.__diagram_events, P = self.permuted(eventSet)
            print(P)
            self.__diagram_coords: np.ndarray = Causet._Permutation_Coords(
                P, 1.0)
        plotReturn = cplt.plot(self.__diagram_events, ax, 'Position',
                               **kwargs)
        if ax is None:
            ax = plt.gca()
        ax.set_axis_off()
        return plotReturn

    def saveAsTikz(self, filename: str) -> None:
        '''
        Computes the Hasse diagram and generates a LaTeX TikZ file that 
        creates a drawing.
        '''
        raise NotImplementedError()
