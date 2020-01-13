import ast
from collections import OrderedDict

from PythonVoiceCodingPlugin.library import sorted_by_source_region,get_source_region,make_flat
from PythonVoiceCodingPlugin.library.info import *
from PythonVoiceCodingPlugin.library.LCA import LCA
from PythonVoiceCodingPlugin.library.level_info import LevelVisitor
from PythonVoiceCodingPlugin.library.partial import partially_parse, line_partial
from PythonVoiceCodingPlugin.library.traverse import search_upwards,search_upwards_log, find_matching,match_node, find_all_nodes,search_upwards_for_parent

from PythonVoiceCodingPlugin.queries.abstract import CollectionQuery
from PythonVoiceCodingPlugin.queries.tiebreak import tiebreak_on_lca
from PythonVoiceCodingPlugin.queries.strategies import adjective_strategy,decode_abstract_vertical,translate_adjective,obtain_result
from PythonVoiceCodingPlugin.queries.strategies import decode_item_selection


class CollectClassName(CollectionQuery):
	label = 'ClassName'
	def handle_single(self,view_information,query_description,extra = {}):
		build, selection, origin = self._preliminary(view_information,query_description,extra)
		if not  build: 
			return None,None
		root,atok,m,r = build 
		definition_node = search_upwards(origin,ast.ClassDef) if query_description["format"]!=1 else root
		name_nodes = [(x.name,0)  for x in find_all_nodes(definition_node,ast.ClassDef)]
		names = list(OrderedDict(name_nodes).keys())
		return names



		

