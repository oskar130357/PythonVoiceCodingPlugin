import ast

from PythonVoiceCodingPlugin.library import sorted_by_source_region,get_source_region,make_flat
from PythonVoiceCodingPlugin.library.selection_node import nearest_node_from_offset,node_from_range
from PythonVoiceCodingPlugin.library.info import *
from PythonVoiceCodingPlugin.library.LCA import LCA 
from PythonVoiceCodingPlugin.library.level_info import LevelVisitor
from PythonVoiceCodingPlugin.library.partial import partially_parse, line_partial
from PythonVoiceCodingPlugin.library.traverse import search_upwards,search_upwards_log, find_matching,match_node, find_all_nodes,search_upwards_for_parent

from PythonVoiceCodingPlugin.queries.abstract import SelectionQuery
from PythonVoiceCodingPlugin.queries.tiebreak import tiebreak_on_lca
from PythonVoiceCodingPlugin.queries.strategies import adjective_strategy,decode_abstract_vertical,translate_adjective,obtain_result

class SelectBigRoi(SelectionQuery):
	"""docstring for BigRoi"""
	multiple_in = True
	def handle_single(self,view_information,query_description,extra = {}):
		f = query_description["format"]
		possibilities = {
			1: self.case_one,2: self.case_two,3: self.case_three,4: self.case_four,
		}
		if query_description["big_roi"]=="same":
			global_data = extra["global_data"]
			try : 
				query_description["big_roi"] = global_data["last_big"]
			except :
				raise Exception("Cannot use same if no other big ROI was used")
		self._register_for_storage(last_big=query_description["big_roi"])			
		return  possibilities[f](view_information,query_description, extra)

	def preliminary(self,view_information,query_description, extra = {}):
		selection = self._get_selection(view_information,extra)
		build = self.general_build 
		if not build  or not build[0]:
			return None,None,None,None
		root,atok,m,r  = build 
		selection = m.forward(selection)
		origin = nearest_node_from_offset(root,atok, selection[0]) if selection[0]==selection[1] else node_from_range(root,atok, selection)
		definition_node = search_upwards(origin,ast.FunctionDef) # ,aybe need to change that in the future 
		# in order to find the outermost function.
		if definition_node  and definition_node.first_token.startpos > selection[1]:
			token = atok.get_token_from_offset(selection[0])
			while token.string.isspace():
				token = atok.prev_token( token )
			s = token.startpos
			origin = nearest_node_from_offset(root,atok, s) 
			definition_node = search_upwards(origin,ast.FunctionDef)
		definition_node  = ( 
			definition_node 
			if definition_node  and query_description["big_roi"] not in ["import statement","import module","import value","class name",
							"base class","decorator"]
			else root
		)
		return build, selection, origin, definition_node

	def decode(self,query_description,build):
		def standard(x):
			return x

		possibilities = {
			"return value": ((ast.Return,ast.Yield,ast.YieldFrom),(),get_return_value),
			"pass":(ast.Pass,(),standard),
			"break":(ast.Break,(),standard),
			"continue":(ast.Continue,(),standard),
			"if condition":(ast.If,(),get_pure_if_condition),
			"else if condition":(ast.If,(),get_elif_condition),
			"while condition":(ast.While,(),get_condition),
			"with clause":(ast.With,(),get_with_items),
			"exception":(ast.ExceptHandler,(),get_exception),
            "exception name":(ast.ExceptHandler,(),get_exception_name),
            "handler":(ast.ExceptHandler,(),get_exception_handler),
			"if expression":(ast.IfExp,(),standard),
			"if expression condition":(ast.IfExp,(),get_condition),
			"if expression body":(ast.IfExp,(),get_body),
			"if expression else" :(ast.IfExp,(),get_else),
			"comprehension condition":(ast.comprehension,(),get_comprehension_condition),
			"comprehension value" : ((ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp),(),get_comprehension_value),
			"assertion message":(ast.Assert,(), get_message),
			"assertion condition":(ast.Assert,(), get_condition),
			"exception raised":(ast.Raise,(),get_raise_exception),
			"raised cause":(ast.Raise,(),get_raise_cause),
			"assignment left":((ast.Assign,ast.AugAssign),(),get_left),
			"assignment right":((ast.Assign,ast.AugAssign),(),get_right),
			"assignment full":((ast.Assign,ast.AugAssign),(),standard),
			"expression statement":(ast.Expr,(),standard),
			"iterable":((ast.For,ast.comprehension),(),get_iterable),
			"iterator":((ast.For,ast.comprehension),(),get_iterator),
			"definition name":((ast.FunctionDef),(),get_definition_name),
			"definition parameter": ((ast.FunctionDef,ast.arg),(),get_arg_from_definition),
			"definition parameter list": (ast.arguments,(),standard),
			 # "parameter annotation" : "parameter annotation",
            "default value": (ast.AST,(),identity(is_default_value)),
			"class name":((ast.ClassDef),(),get_class_name),
			"import statement":((ast.Import,ast.ImportFrom),(),get_fixed_import),
			"import module":((ast.Import,ast.ImportFrom),(),get_module),
			"import value" : ((ast.Import,ast.ImportFrom),(),get_fixed_import_value),
			"lambda":((ast.Lambda),(),standard),
            "lambda body":((ast.Lambda),(),get_body),
            "if body":((ast.If, ast.For,ast.comprehension),(),get_body),
            # "definition parameter": ((ast.arg),(),get_definition_parameter_name),
            "decorator":((ast.AST),(),identity(is_decorator)),
            "base class":((ast.AST),(),identity(is_base)),

            # to be removed with the next release 
            "string":((ast.Str),(),standard),
            "integer literal":((ast.Num),(),standard),
            "dictionary":((ast.Dict),(),standard),
            "set":((ast.Set),(),standard),
            "tuple":((ast.Tuple),(),standard),
            "list":((ast.List),(),standard),

            "subscript":((ast.Subscript),(),standard),
            "subscript body":((ast.Subscript),(),get_subscript_body),
            "key":((ast.Subscript),(),get_subscript_key),
            "lower":((ast.Slice),(),get_slice_lower),
            "upper":((ast.Slice),(),get_slice_upper),
            "step":((ast.Slice),(),get_slice_step),
            
            "attribute":((ast.Attribute),(),standard),
            "comparison":((ast.Compare),(),standard),
            "arithmetic":((ast.BinOp),(),get_arithmetic),
            "boolean":((ast.BoolOp),(),get_boolean),

            "container":((ast.Compare),(),get_container_check),
            "member":((ast.Compare),(),get_member_check),
            "membership":((ast.Compare),(),get_membership),
            
            "left side":((ast.Compare),(),get_comparison_left_side),
            "right side":((ast.Compare),(),get_comparison_right_side),
            "middle":((ast.Compare),(),get_comparison_middle),

            "arithmetic left":((ast.BinOp),(),get_arithmetic_left),
            "arithmetic right":((ast.BinOp),(),get_arithmetic_right),
            "arithmetic middle":((ast.BinOp),(),get_arithmetic_middle),

            "boolean left":((ast.BoolOp),(),get_boolean_left),
            "boolean right":((ast.BoolOp),(),get_boolean_right),
            "boolean middle":((ast.BoolOp),(),get_boolean_middle),

            "boolean and":((ast.BoolOp),(),get_boolean_and),
            "boolean or":((ast.BoolOp),(),get_boolean_or),



		}

		temporary  = possibilities[query_description["big_roi"]]
		basic_information = make_information(temporary[2],atok = build[1] if build else None)
		if "sub_index" in query_description:
			index = query_description["sub_index"]
			def modified_information(x, information,index):
				data  = information(x)
				return get_sub_index(data,index)

			y  = lambda x: basic_information(x)
			y.secondary  = lambda x: modified_information(x,basic_information,index-1)
			return (temporary[0],temporary[1],y)
		else:
			return  possibilities[query_description["big_roi"]][:2] + (basic_information,)


	def case_one(self,view_information,query_description, extra = {}):
		################################################################	
		#		<big_roi>
		###############################################################	
		build, selection, origin, definition_node = self.preliminary(view_information, query_description,extra)
		targets, exclusions, information  =  self.decode(query_description,build)
		information = getattr(information,"secondary",information)
		selector = lambda x:match_node(x,targets,exclusions) and generic_fix(x,build[1])
		candidates = tiebreak_on_lca(definition_node,origin,find_all_nodes(definition_node, selector = selector))
		candidates = [information(x)  for x in candidates if information(x)]
		result, alternatives = obtain_result(None, candidates)
		return  self._backward_result(result, alternatives,build)


	def case_two(self,view_information,query_description, extra = {}):
		################################################################	
		#		<adjective> <big_roi>
		###############################################################	
		build, selection, origin, definition_node = self.preliminary(view_information, query_description,extra)
		targets, exclusions, information  =  self.decode(query_description,build)
		root,atok,m,r  = build 
		temporary_information = lambda x: information(x) if match_node(x,targets,exclusions)  and generic_fix(x,atok) else None
		additional_parameters = {}
		

		if selection[0]!=selection[1]:
			additional_parameters["small_root"] = origin
			additional_parameters["penalized"] = [origin]
		additional_parameters["only_information"] = True
		# just looking on the shape of this code you know there's a bug in here somewhere:)
		result, alternatives = adjective_strategy(
				atok=atok,
				root = definition_node,
				adjective_word = query_description["nth"],
				level_nodes = find_all_nodes(definition_node, (ast.If,ast.While,ast.For,ast.Try,ast.With,ast.FunctionDef,ast.ClassDef)),
				information_nodes = find_matching(definition_node,temporary_information),
				**additional_parameters
		)
		print("result, alternatives",result, alternatives,"\n")
		information = getattr(information,"secondary",information)
		result = information(result) if result else None
		alternatives  =[ information(x)  for x in alternatives] if alternatives else []
		return  self._backward_result(result, alternatives,build)


	def case_three(self,view_information,query_description, extra = {}):
		################################################################	
		# <vertical_abstract_only_direction> [<ndir>] <big_roi> [<big_roi_sub_index>]
		###############################################################	
		build, selection, origin, definition_node = self.preliminary(view_information, query_description,extra)
		targets, exclusions, information  =  self.decode(query_description,build)
		root,atok,m,r  = build
		temporary_information = lambda x: information(x) if match_node(x,targets,exclusions) and generic_fix(x,atok) else None

		direction = query_description["vertical_direction"]
		ndir = query_description["ndir"]
		row, column = view_information["rowcol"](m.backward(selection)[0])

		# bug fixing
		test_result = decode_abstract_vertical(root,atok,targets,row+1, 1,direction,True,
					temporary_information,want_alternatives = False)
		l = search_upwards_log(origin,ast.stmt)
		if test_result in [l[0]] + l[1]  and row + 1>=test_result.first_token.start[0]:
			ndir  = ndir + 1
			


		result,alternatives = decode_abstract_vertical(root,atok,targets,row+1, ndir,direction,True,
					temporary_information,want_alternatives = True)

		if result:
			new_definition_node = search_upwards(result,ast.FunctionDef)
			if definition_node is not new_definition_node  and new_definition_node is not None:
				alternatives  = tiebreak_on_lca(new_definition_node,result,find_all_nodes(new_definition_node,targets , exclusions))

		result, alternatives = obtain_result(result, alternatives)
		information = getattr(information,"secondary",information)
		result = information(result) if result else None
		alternatives  = [information(x)  for x in alternatives] if alternatives else []
		return  self._backward_result(result, alternatives,build)


	def case_four(self,view_information,query_description, extra = {}):
		################################################################	
		# [smart] <vertical_abstract_only_direction> [<ndir>] <block> [<adjective>] <big_roi> [<big_roi_sub_index>]
		###############################################################	
		build, selection, origin, definition_node = self.preliminary(view_information, query_description,extra)
		targets, exclusions, information  =  self.decode(query_description,build)
		temporary_information = lambda x: match_node(x,ast.FunctionDef) 
		root,atok,m,r  = build

		direction = query_description["vertical_direction"]
		ndir = query_description["ndir"]
		row = view_information["rowcol"](m.backward(selection)[0])[0] + 1 if definition_node is root else definition_node.first_token.start[0]
		bonus = 1 if definition_node.first_token.startpos > selection[1]  else 0
		t = decode_abstract_vertical(root,atok,targets,row, ndir + bonus,direction,True,temporary_information)
		if "nth" not in query_description:
			information = getattr(information,"secondary",information)
			selector = lambda x:match_node(x,targets,exclusions) and generic_fix(x,build[1])
			candidates = tiebreak_on_lca(root,definition_node,find_all_nodes(t, selector = selector))
			candidates = [information(x)  for x in candidates if information(x)]
			result, alternatives = obtain_result(None, candidates)
			return  self._backward_result(result, alternatives,build)
		else:
			additional_parameters = {}
			result, alternatives = adjective_strategy(
				atok=atok,
				root = t,
				adjective_word = query_description["nth"],
				level_nodes = find_all_nodes(t,(ast.If,ast.While,ast.For,ast.Try,ast.With,ast.FunctionDef)),
				information_nodes = find_matching(t,lambda x: information(x) if match_node(x,targets,exclusions) else None),
				**additional_parameters
			)
			information = getattr(information,"secondary",information)
			result = information(result) if result else None
			alternatives  =[ information(x)  for x in alternatives] if alternatives else []
			return  self._backward_result(result, alternatives,build)
















