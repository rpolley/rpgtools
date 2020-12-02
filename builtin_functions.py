from util import cartesian_product, fold
from collections import defaultdict
def builtins_distribution(item):
	return dict(item.distribution())

def builtins_distribution_distribution(item):
	return item

def builtins_max(seq):
	return max(seq.sequence())

def builtins_max_distribution(seq):
	distr_seq = seq.distribution_sequence()
	m = {(-float('inf'),): 1.0}
	for distr in distr_seq:
		m = fold(cartesian_product(m, distr), max)
	return m

def builtins_if(test, **kwargs):
	then, els = kwargs['then'], kwargs['else']
	#print(kwargs)
	if test.eval() != 0:
		return then[0].eval()
	else:
		return els[0].eval()

def builtins_if_distribution(test, **kwargs):
	then, els = kwargs['then'], kwargs['else']
	test_distr = test.distribution()
	els_chance = test_distr[0]
	then_chance = 1.0 - els_chance
	result = defaultdict(lambda: 0.0)
	for t, p in then.distribution().items():
		result[t] += p*then_chance
	for e, p in els.distribution().items():
		result[e] += p*els_chance
	return result 

