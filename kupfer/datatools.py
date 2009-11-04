import itertools

class SavedIterable (object):
	"""Wrap an iterable and cache it.

	The SavedIterable can be accessed streamingly, while still being
	incrementally cached. Later attempts to iterate it will access the
	whole of the sequence.

	When it has been cached to its full extent once, it reduces to a
	thin wrapper of a sequence iterator. The SavedIterable will pickle
	into a list.

	>>> r = list(range(5))
	>>> s = SavedIterable(iter(r))
	>>> next(iter(s))
	0
	>>> list(s)
	[0, 1, 2, 3, 4]

	>>> type(iter(s)) is type(iter([]))
	True

	>>> import pickle
	>>> pickle.loads(pickle.dumps(s))
	[0, 1, 2, 3, 4]

	>>> u = SavedIterable(iter(r))
	>>> one, two = iter(u), iter(u)
	>>> next(one), next(two)
	(0, 0)
	>>> list(two)
	[1, 2, 3, 4]
	>>> list(one)
	[1, 2, 3, 4]

	>>> SavedIterable(r)
	[0, 1, 2, 3, 4]
	"""
	def __new__(cls, iterable):
		if isinstance(iterable, list):
			return iterable
		return object.__new__(cls)
	def __init__(self, iterable):
		self.iterator = iter(iterable)
		self.data = []
	def __iter__(self):
		if self.iterator is None:
			return iter(self.data)
		return self._incremental_caching_iter()
	def _incremental_caching_iter(self):
		indices = itertools.count()
		while True:
			idx = next(indices)
			try:
				yield self.data[idx]
			except IndexError:
				pass
			else:
				continue
			if self.iterator is None:
				return
			try:
				x = next(self.iterator)
				self.data.append(x)
				yield x
			except StopIteration:
				self.iterator = None
	def __reduce__(self):
		# pickle into a list with __reduce__
		# (callable, args, state, listitems)
		return (list, (), None, iter(self))

if __name__ == '__main__':
	import doctest
	doctest.testmod()
