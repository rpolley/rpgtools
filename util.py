from collections import defaultdict
def cartesian_product(lhs, rhs):
	result = {}
	for k1, p1 in lhs.items():
		for k2, p2 in rhs.items():
			result[(*k1, *k2)] = p1*p2
	return result

def fold(distr, func):
	result = defaultdict(lambda: 0.0)
	for k, p in distr.items():
		result[func(*k),] += p
	return result

