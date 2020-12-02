from builtin_functions import * 
from collections import defaultdict
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

context = {}
# represents an expression which assigns a value to a variable
class VariableSetter(Expression):
	def __init__(self, varname, value):
		self.varname = varname.eval()
		self.value = value
	def eval(self):
		context[self.varname] = self.value.eval()

# represents an expression which gets a value from a variable
class VariableGetter(Expression):
	def __init__(self, varname):
		self.varname = varname
	def eval(self):
		return context[self.varname.eval()]

