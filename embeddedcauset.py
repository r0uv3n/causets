#!/usr/bin/env python
'''
Created on 20 Jul 2020

@author: Christoph Minz
'''
from __future__ import annotations
from typing import Set, List, Iterable, Dict, Tuple, Callable, Any, Union
import numpy as np
from event import CausetEvent
from causet import Causet
from shapes import CoordinateShape
from spacetimes import Spacetime, FlatSpacetime
import causet_plotting as cs_plt
from matplotlib import axes as plta


class EmbeddedCauset(Causet):
    '''
    Handles a causal set that is embedded in a subset of a spacetime manifold.
    '''

    _shape: CoordinateShape
    _spacetime: Spacetime

    def __init__(self,
                 dim: int = 2,
                 spacetime: Spacetime = None,
                 shape: Union[str, CoordinateShape] = None,
                 coordinates: Union[Iterable[Iterable[float]],
                                    np.ndarray] = None) -> None:
        '''
        Generates an embedded causal set in a spacetime subset of a specified 
        (coordinate) shape and with the events specified by `causet` and 
        `coordinates`.

        Optional arguments:
        `dim`: int
        Default dimension of the embedding spacetime. This parameter will be 
        ignored if a spacetime object is specified or if a shape is specified 
        as `CoordinateShape`. Default: 2
        A `ValueError` is raised if this argument is less than 1.

        `spacetime`: `Spacetime` object
        A spacetime object (including parameters) that determines the 
        causality and lightcones. Default: `FlatSpacetime` of dimension `dim`.

        `shape`: str or `CoordinateShape` object
        (The name of) a coordinate shape object that ranges over the embedding 
        region. If no shape is specified (default), the method 
        `DefaultShape()` of the spacetime object is called. For the default 
        spacetime `FlatSpacetime` the default shape is a unit diamond 
        (Alexandrov subset).
        A `ValueError` is raised if the specified shape has a different 
        dimension than the spacetime.

        `coordinates`: np.ndarray
        Matrix with a row for each event's coordinates to be created in the 
        embedding.
        A `ValueError` is raised if the specified coordinates have a 
        different dimension than the spacetime.
        '''
        super().__init__(set())
        # initialise dimension and spacetime:
        if isinstance(shape, CoordinateShape):
            dim = shape.Dim
        if spacetime is None:
            if dim < 1:
                raise ValueError('The dimension must be an integer ' +
                                 'of at least 1.')
            spacetime = FlatSpacetime(dim)
        self._spacetime = spacetime
        dim = spacetime.Dim
        # initialise shape:
        if shape is None:
            shape = spacetime.DefaultShape()
        elif isinstance(shape, str):
            shape = CoordinateShape(dim, shape)
        if shape.Dim != dim:
            raise ValueError('The dimension of the specified coordinate ' +
                             'shape is different from the dimension of the ' +
                             'spacetime.')
        self._shape = shape
        # create new events:
        if coordinates is not None:
            # add labelled event with coordinates:
            if isinstance(coordinates, np.ndarray) and \
                    ((coordinates.ndim != 2) or (coordinates.shape[1] != dim)):
                raise ValueError('The dimension of the specified coordinates ' +
                                 'is different from the embedding dimension.')
            self.create(coordinates)

    @staticmethod
    def FromPermutation(P: List[int], labelFormat: str = None,
                        radius: float=1.0) -> 'EmbeddedCauset':
        '''
        Generates a causal set from the permutation P of integers from 1 
        to len(P) - that can be embedded in an Alexandrov subset of 
        Minkowski spacetime.
        '''
        C: EmbeddedCauset = EmbeddedCauset(
            shape=CoordinateShape(2, 'diamond', radius=radius))
        C.create(Causet._Permutation_Coords(P, radius), labelFormat)
        return C

    @property
    def Shape(self) -> CoordinateShape:
        '''
        Returns the CoordinateShape object of the embedding region.
        '''
        return self._shape

    @property
    def Dim(self) -> int:
        '''
        Returns the CoordinateShape object of the embedding region.
        '''
        return self.Shape.Dim

    @property
    def Density(self) -> float:
        '''
        Returns the density of events as ratio of the set cardinality to 
        the embedding shape's volume.
        '''
        return float(self.Card) / self.Shape.Volume

    @property
    def LengthScale(self) -> float:
        '''
        Returns the fundamental length scale as inverse d-root of 
        `self.Density` if `card > 0`, else 0.0. 
        '''
        return 0.0 if self.Card == 0 \
            else self.Density**(1.0 / self.Shape.Dim)

    def create(self, coordinates: Union[Iterable[Iterable[float]],
                                        Iterable[np.ndarray],
                                        np.ndarray],
               labelFormat: str = None,
               relate: bool = True) -> Set[CausetEvent]:
        '''
        Creates new event with the specified coordinates, adds them to 
        this instance and returns the new set of event.
        The argument 'coordinates' has to be List[List[float]], 
        List[np.ndarray] or np.ndarray (matrix with a coordinate row for 
        each event).
        '''
        n: int = self.Card + 1
        eventSet: Set[CausetEvent] = {CausetEvent(label=n + i
                                                  if labelFormat is None
                                                  else labelFormat.format(n + i),
                                                  coordinates=c)
                                      for i, c in enumerate(coordinates)}
        self._events.update(eventSet)
        if relate:
            self.relate()
        return eventSet

    def relate(self, link: bool=True) -> None:
        '''
        Resets the causal relations between all event based on their 
        embedding in the given spacetimes manifold.
        '''
        _iscausal: Callable[[np.ndarray, np.ndarray],
                            Tuple[bool, bool]] = self._spacetime.Causality()
        for e in self._events:
            e._prec = set()
            e._succ = set()
        eventList: List[CausetEvent] = list(self._events)
        eventList_len: int = len(eventList)
        for i, a in enumerate(eventList):
            for j in range(i + 1, eventList_len):
                b = eventList[j]
                isAB, isBA = _iscausal(a.Coordinates, b.Coordinates)
                if isAB:  # A in the past of B:
                    a._succ.add(b)
                    b._prec.add(a)
                if isBA:  # A in the future of B:
                    b._succ.add(a)
                    a._prec.add(b)
        if link:
            self.link()
        else:
            self.unlink()

    def relabel(self, dim: int = 0, descending: bool = False) -> None:
        '''
        Resets the labels of all event to ascending (default) or 
        descending integers (converted to str) corresponding to the 
        coordinate component in dimension 'dim'.
        '''
        eventList = list(self._events)
        sorted_idx = np.argsort(np.array(
            [e.Coordinates[dim] for e in eventList]))
        if descending:
            sorted_idx = np.flip(sorted_idx)
        for i, idx in enumerate(sorted_idx):
            eventList[idx].Label = i + 1

    def _init_plotting(self, plotArgs: Dict[str, Any],
                       plotEvents: List[CausetEvent]=None) -> \
            Tuple[List[CausetEvent], Dict[str, Any]]:
        '''
        Handles the plot keyword parameter 'axislim' == 'shape' (Default) 
        and initialises the plotting coordinates.
        '''
        # handle keyword parameter axislim='shape' (default)
        dims: List[int]
        try:
            dims = plotArgs['dims']
        except KeyError:
            plotArgs.update({'dims': [1, 0]})
            dims = [1, 0]
        if ('axislim' not in plotArgs) or (plotArgs['axislim'] == 'shape'):
            if len(dims) > 2:
                edgehalf: float = self.Shape.MaxEdgeHalf(dims)
                center: np.ndarray = self.Shape.Center
                center0: float = center[dims[0]]
                center1: float = center[dims[1]]
                center2: float = center[dims[2]]
                plotArgs.update({'axislim': {
                    'xlim': (center0 - edgehalf, center0 + edgehalf),
                    'ylim': (center1 - edgehalf, center1 + edgehalf),
                    'zlim': (center2 - edgehalf, center2 + edgehalf)}})
            else:
                plotArgs.update({'axislim': {
                    'xlim': self.Shape.Limits(dims[0]),
                    'ylim': self.Shape.Limits(dims[1])}})
        # get event list and copy coordinates to memory:
        if plotEvents is None:
            plotEvents = list(self._events)
        return (plotEvents, plotArgs)

    def TimeslicePlotter(self, ax: plta.Axes = None,
                         eventList: List[CausetEvent] = None,
                         **kwargs) -> Callable[[np.ndarray], Dict[str, Any]]:
        '''
        Returns the core plotter function handle that requires an array of 
        one or two time values (as past and future time). The plotter function 
        creates a plot of this instance (or the list of event if eventList 
        is not None) into the Axes ax with plot parameters given by keyword 
        arguments. To fit the axis limits to the embedding shape, use the 
        keyword argument 'axislim' == 'shape' (Default).
        For all other plot options, see doc of 
        causet_plotting.plot_parameters.
        '''
        pEvents, pArgs = self._init_plotting(kwargs, eventList)
        return cs_plt.Plotter(pEvents, ax, spacetime=self._spacetime, **pArgs)

    def plot(self, ax: plta.Axes = None,
             eventList: List[CausetEvent] = None,
             **kwargs) -> Dict[str, Any]:
        '''
        Creates a plot of this instance (or the list of event if eventList 
        is not None) into the Axes ax with plot parameters given by keyword 
        arguments. To fit the axis limits to the embedding shape, use the 
        keyword argument 'axislim' == 'shape' (Default).
        For all other plot options, see doc of 
        causet_plotting.plot_parameters.
        '''
        pEvents, pArgs = self._init_plotting(kwargs, eventList)
        return cs_plt.plot(pEvents, ax, spacetime=self._spacetime, **pArgs)
