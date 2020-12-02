from collections import defaultdict
def cartesian_product(lhs, rhs):
	result = {}
	for k1, p1 in lhs.items():
		for k2, p2 in rhs.items():
			result[(*k1, *k2)] = p1*p2
	return result

def zero_vector():
	return defaultdict(lambda: 0.0)

def fold(distr, func):
	result = zero_vector() 
	for k, p in distr.items():
		result[func(*k),] += p
	return result

def scalar_product_accumulate(distr, scalar, to=None):
	if to == None:
		to = zero_vector()
	for k, p in distr.items():
		to[k] += p*scalar
	return to
