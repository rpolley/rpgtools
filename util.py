from collections import defaultdict
# takes the cartesian product of two probability distributions
# i.e. given A, B are pdfs and a <= A, b <= B, what is the probability of `a and b`
def cartesian_product(lhs, rhs):
	result = {}
	for k1, p1 in lhs.items():
		for k2, p2 in rhs.items():
			result[(*k1, *k2)] = p1*p2
	return result

def zero_vector():
	return defaultdict(lambda: 0.0)

# apply a function to the keys of a distribution, keeping the probabilities the same
def fold(distr, func):
	result = zero_vector() 
	for k, p in distr.items():
		result[func(*k),] += p
	return result

# scale the probabilitys in a distribution by an amount, and accumulate it into another distribution
def scalar_product_accumulate(distr, scalar, to=None):
	if to == None:
		to = zero_vector()
	for k, p in distr.items():
		to[k] += p*scalar
	return to
