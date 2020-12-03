from builtin_functions import * 
from collections import defaultdict, ChainMap
from random import randrange
from util import cartesian_product, fold, scalar_product_accumulate
from functools import reduce

# base class for an internal object
class Expression():
	# get the result of viewing the object as a single item
	def eval(self):
		raise NotImplementedError
	# get the result of viewing the object as a sequence of items
	def sequence(self):
		return [self.eval()]

# subclass of expressions that support probability distributions
class ValueExpression(Expression):
	# get the ressult of viewing the object as a probability distribution
	def distribution(self):
		raise NotImplementedError
	# get the result of viewing the object as a sequence of probability distributions
	def distribution_sequence(self):
		return [self.distribution()]

# class that directly wraps a python object
class Literal(ValueExpression):
	def __init__(self, value):
		self.value = value
	# return the wrapped value
	def eval(self):
		return self.value
	# return a probability distribution where the wrapped value has a 100% chance of occuring
	def distribution(self):
		return {(self.value,): 1.0}

# literal that wrapps an integer
class IntegerLiteral(Literal):
	def __init__(self, value):
		# cast the value to an integer before storing it
		self.value = int(value)
	def __repr__(self):
		return "IntegerLiteral({})".format(self.value)

# result of taking some basic mathmatical operation of two expressions
class MathExpression(ValueExpression):
	# look up table mapping operators to functions that do the operation
	operators = {
		'+' : (lambda x, y: x + y),
		'-' : (lambda x, y: x - y),
		'*' : (lambda x, y: x * y),
		'/' : (lambda x, y: x / y),
		'==' : (lambda x, y: 1 if x == y else 0),
		'!=' : (lambda x, y: 1 if x == y else 0),
		'<' : (lambda x, y: 1 if x < y else 0),
		'>' : (lambda x, y: 1 if x > y else 0),
		'>=' : (lambda x, y: 1 if x >= y else 0),
		'<=' : (lambda x, y: 1 if x <= y else 0),
	}
	def __init__(self, lhs, operator, rhs):
		self.operator = MathExpression.operators[operator.eval()]
		self.lhs = lhs
		self.rhs = rhs
	# just apply the operation
	def eval(self):
		return self.operator(self.lhs.eval(), self.rhs.eval())
	def distribution(self):
		product = cartesian_product(self.lhs.distribution(), self.rhs.distribution())
		return fold(product, self.operator)

# result of an expression like '1d6'
class DiceExpression(ValueExpression):
	def __init__(self, number, sides):
		self.number, self.sides = number, sides
	def	eval(self):
		return sum(self.sequence())
	def sequence(self):
		sides = self.sides.eval()
		number = self.number.eval()
		return [randrange(1,sides+1) for _ in range(number)]
	# get a pdf representing a dice with `sides` sides
	def dice_pdf(sides):
		result = {}
		for i in range(1, sides+1):
			result[(i,)] = 1.0/sides
		return result
	def distribution(self):
		# this would be very simple if number or sides couldn't themselves have non-trivial probability distributions
		# get the pdf of there being n dice with m sides
		qual_pdf = cartesian_product(self.number.distribution(), self.sides.distribution())
		result = None
		for k, p in qual_pdf.items():
			number, sides = k
			# get the expanded pdf for this combo of number and sides
			expanded = [DiceExpression.dice_pdf(sides) for _ in range(number)]
			def sum_pdf(lhs, rhs):
				return fold(cartesian_product(lhs, rhs), lambda x, y: x + y)
			# combine into a distribution
			total_pdf = reduce(sum_pdf, expanded)
			# accumulate into the ressult distribution
			result = scalar_product_accumulate(total_pdf, p, result)
		return result
	def distribution_sequence(self):
		# simmilar to distribution, but we need to handle the dice independently
		number_distr = self.number.distribution()
		sides_distr = self.sides.distribution()
		max_dice, = max(number_distr.keys())
		dice = []
		# iterate throuch the nth die
		for dn in range(1,int(max_dice)+1):
			# first calculate the probability of this die existing
			dn_unit = {(dn,): 1.0}
			at_least_dn = fold(cartesian_product(number_distr, dn_unit), lambda x, y: y <= x)
			dn_exists_prob = at_least_dn[True,]
			# calculate the pdf of the dice, weighted by the chance of it existing
			dice_n = None
			for sides, sides_p in sides_distr.items():
				sides, = sides
				dice_n = scalar_product_accumulate(DiceExpression.dice_pdf(sides), sides_p*dn_exists_prob, dice_n)
			#todo: handle this better
			# what is a way that makes sense to encode "this dice doesn't exist" in a dice's pdf?
			# account for the chance of the die not existing
			dice_n = scalar_product_accumulate({(0.0,) : 1.0}, 1-dn_exists_prob, dice_n)
			dice.append(dice_n)
		return dice			

# represent a call to a function in the parsed language
class FunctionCall(Expression):
	# lookup table for functions to use when taking the value
	symbols = {
		('max', 1, ()) : builtins_max,
		('if', 1, (('then', 1), ('else', 1))): builtins_if,
		('distribution', 1, ()): builtins_distribution,
	}
	# lookup table for functions to use when taking the distribution
	distr_symbols = {
		('max', 1, ()) : builtins_max_distribution,
		('if', 1, (('then', 1), ('else', 1))): builtins_if_distribution,
		('distribution', 1, ()): builtins_distribution_distribution,
	}
	def __init__(self, funame, args):
		# save the args
		args = args.sequence()
		self.args = args[0].sequence()
		self.kwargs = {s[0].eval(): s[1:] for s in [s.sequence() for s in args[1:]]}
		# construct the key to use when looking up this function
		self.kwargsets = tuple([(kw, len(s)) for kw, s in self.kwargs.items()])
		self.funame = (funame.eval(), len(self.args), self.kwargsets)
	def eval(self):
		# lookup the function and call it
		function = FunctionCall.symbols[self.funame]
		return function(*self.args, **self.kwargs)
	def distribution(self):
		# lookup the function and call it
		function = FunctionCall.distr_symbols[self.funame]
		return function(*self.args, **self.kwargs)

# helper class for turning syntactic lists of items into a python list wrapped in an expression
# when it's constructed in the parser's transform method, it's initially a sort of linked list,
# consisting of a head that's an expression, and optionally a tail consisting of a Listconverter
# containing the rest of the list
class ListConverter(Expression):
	def __init__(self, head, tail=None):
		if tail:
			# unpack the rest of the list, and append it to the head
			self.value = [head] + tail.sequence()
		else:
			# no tail, so just add the head to the list
			self.value = [head]
	def sequence(self):
		# since the wrapped value is already a sequence, return it
		return self.value
	def eval(self):
		return [item.eval() for item in self.value]
	def __repr__(self):
		return "ListConverter({})".format(self.value)

class Context:
	def top():
		return Context._context
	_context = ChainMap()

# represents an expression which assigns a value to a variable
class VariableSetter(ValueExpression):
	def __init__(self, varname, value):
		self.varname = varname.eval()
		self.value = value
		self.context = Context.top()
	def eval(self):
		self.context[self.varname] = self.value.eval()
	def distribution(self):
		self.context[self.varname] = self.value.distribution()

# represents an expression which gets a value from a variable
class VariableGetter(ValueExpression):
	def __init__(self, varname):
		self.varname = varname
		self.context = Context.top()
	def lookup(self):
		return self.context[self.varname.eval()]
	def _eval(self, method):
		val = self.lookup()
		if hasattr(val, method):
			eval_method = getattr(val, method)
			return eval_method()
		else:
			return val
	def eval(self):
		return self._eval('eval')
	def distribution(self):
		return self._eval('distribution')

class Block(ValueExpression):
	def __init__(self, statements):
		self.statements = statements.sequence()
		self.prepared = False
		self.context = None
	def block_prepare(self, parent_context = None):
		if self.prepared:
			return
		if parent_context == None:
			self.context = Context.top()
		else:
			self.context = parent_context.new_child()

		for statement in self.statements:
			if hasattr(statement, 'block_prepare'):
				statement.block_prepare(self.context)
			elif hasattr(statement, 'context'):
				statement.context = self.context
		self.prepared = True
	def _eval(self, method):
		self.block_prepare()
		output = None
		for statement in self.statements:
			eval_method = getattr(statement, method)
			sval = eval_method()
			if type(statement) == ReturnStatement:
				output = sval
				break
		self.prepared = False
		return output
	def eval(self):
		return self._eval('eval')
	def distribution(self):
		return self._eval('distribution')

class ReturnStatement(ValueExpression):
	def __init__(self, wrapped):
		self.wrapped = wrapped
	def eval(self):
		return self.wrapped.eval()
	def distribution(self):
		return self.wrapped.distribution()
	def distribution_sequence(self):
		return self.wrapped.distribution_sequence()
	def sequence(self):
		return self.wrapped.sequence()

class FunctionSignature():
	def __init__(self, name, argslist, kwargslist=None):
		self._name = name
		self.argslist = argslist.sequence()
		if kwargslist:
			self.kwargslist = [(kwargset[0].eval(), kwargset[1].sequence()) for kwargset in kwargslist.sequence()]
		else:
			self.kwargslist = None
	def name(self):
		argsnum = len(self.argslist)
		if self.kwargslist:
			kwargs_nums = tuple([(kwargset[0], len(kwargset[1])) for kwargset in self.kwargslist])
		else:
			kwargs_nums = ()
		return (self._name.eval(), argsnum, kwargs_nums)
	def bind_function(self):
		def bind(*args, **kwargs):
			binds = []
			for i in range(len(self.argslist)):
				varname = self.argslist[i]
				value = args[i]
				varset = VariableSetter(varname, value)
				binds.append(varset)
			if self.kwargslist:
				for kwargset in self.kwargslist:
					kwarg_key = kwargset[0]
					passed_kwargs = kwargs[kwarg_key]
					kwargset_kwargs = kwargset[1]
					for i in range(len(kwargset_kwargs)):
						varname = kwargset_kwargs[i]
						value = passed_kwargs[i]
						varset = VariableSetter(varname, value)
						binds.append(varset)
			return binds
		return bind

class ListWrapper(Literal):
	def sequence(self):
		return self.value
	def distribution_sequence(self):
		return [v.distribution() for i in self.value]

class FunctionDeclaration(Expression):
	def __init__(self, signature, block):
		self.signature = signature
		self.block = block
		self.bind = signature.bind_function()
	def eval(self):
		def call(*args, **kwargs):
			binds = self.bind(*args, **kwargs)
			statements = self.block.statements
			return Block(ListWrapper(binds+statements))
		def eval_call(*args, **kwargs):
			runblock = call(*args, **kwargs)
			return runblock.eval()
		def distribution_call(*args, **kwargs):
			runblock = call(*args, **kwargs)
			return runclock.distribution()
		FunctionCall.symbols[self.signature.name()] = eval_call
		print(FunctionCall.symbols)
		FunctionCall.distr_symbols[self.signature.name()] = distribution_call
	