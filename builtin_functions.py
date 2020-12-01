def builtins_distribution(item):
	return dict(item.distribution())

def builtins_max(seq):
	return max([_builtins_eval(item) for item in seq.sequence()])

def builtins_if(test, **kwargs):
	then, els = kwargs['then'], kwargs['else']
	#print(kwargs)
	if test.eval() != 0:
		return then[0].eval()
	else:
		return els[0].eval()


