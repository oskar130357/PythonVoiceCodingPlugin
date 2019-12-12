from copy import deepcopy

from PythonVoiceCodingPlugin.queries import *
from PythonVoiceCodingPlugin.application.build_cache import BuildCache
from PythonVoiceCodingPlugin.interface.common.actions import *


class Application():
	"""docstring for Application"""
	active_applications = {}
	build_cache  = BuildCache()
	global_state = {}
	
	def __init__(self,vid):
		self.history = []
		self.state = {}
		self.ui_controller = None
		self.vid = vid

	def create_application_for_view(vid):
		if vid not in Application.active_applications:
			Application.active_applications[vid] = Application(vid)

	def get_application(vid):
		Application.create_application_for_view(vid)
		return Application.active_applications[vid]

	def update_state(self,view_information,code):
		'''		
		normally I would like these to be implemented by means of modification handlers
		And an event listener transmitting every chains in the code. However it seems
		but the provided event listener does not provide me with the location that was changed.
		So in order to keep track over the location of important regions when the code changes,
		The current solution is to outsource everything to the sublime add_regions/get_regions 
		functionality
		'''
		self.state["result"] = view_information["get_regions"]("result")
		self.state["alternatives"] = view_information["get_regions"]("alternatives")
		self.state["origin"] = view_information["get_regions"]("origin")
		self.state["origin_stack"] = view_information["get_regions"]("origin_stack")

	


	def respond_to_query(self,interface,query_description,secondary=False):
		extra = {"state":self.state,"global_state":Application.global_state,"history":self.history}
		view_information  = interface.get_view_information()
		ui_information = interface.get_ui_information()

		# extract code and change count and reuse previous build if possible
		code = view_information["code"]
		change_count = view_information["change_count"]
		latest_build = Application.build_cache.get_build(self.vid,change_count)

		# get the corresponding query and execute it
		s = get_query(query_description)(code,latest_build)
		secondary_query_description = get_secondary_query(query_description)
		if secondary_query_description:
			backup=[deepcopy(self.state),deepcopy(self.global_state)]
		try:
			s(view_information,query_description,extra)
		except:
			pass

		# check if there are exceptions
		if s.exceptions_raised:
			interface.clear_actions()
			interface.push_action(PopUpErrorAction(str(s.exceptions_raised)))
			return False

		# register build for later use
		b = s.get_the_latest_build()
		if b:
			Application.build_cache.register_build(self.vid,change_count,b)

		if isinstance(s,SelectionQuery):
			result = s.result 
			alternatives  = s.alternatives
			# self.state["result"]  = None
			# self.state["alternatives"] = []
			if result:
				self.state["result"] = result
				self.state["alternatives"] = []
				self.state["alternatives_text"] = []
				self.state["result_text"] = code[result[0]:result[1]]
				interface.push_action(SelectionAction(result))
				self.history.append(("selection",view_information["change_count"],view_information["selection"],result))
			interface.push_action(ClearHighlightAction("alternatives"))
			if alternatives:
				self.state["alternatives"] = alternatives
				self.state["alternatives_text"] = [code[x[0]:x[1]] for x in alternatives]
				interface.push_action(DisplayRegionsAction("alternatives",alternatives,"Alternatives:\n"))
				interface.push_action(HighlightCleverAction(alternatives,"alternatives",result))
				
		elif isinstance(s,InsertionQuery):
			output = s.writing_locations_text
			selections = s.optional_selection
			if output:
				for location, text in output:
					interface.push_action(ReplaceAction(location,text))
				self.history.append(("insert"))
			if selections:
				interface.push_action(SelectionAction(selections))
		
		elif isinstance(s,CollectionQuery):
			result = s.result
			items = s.items
			writing_positions = s.writing_positions
			selections = s.optional_selection
			if result:
				for location in writing_positions:
					interface.push_action(ReplaceAction(location,result))
			if items:
				print(s.label,"labeling\n")
				interface.push_action(DisplayNiceAction(s.label,items,True))  
				self.state["collection"] = items
				self.global_state["collection"] = items
				self.history.append(("collect"))
			if selections:
				interface.push_action(SelectionAction(selections))

		if secondary_query_description:
			interface.push_action(ClearHighlightAction("alternatives"))
			secondary_success = self.respond_to_query(interface,secondary_query_description,secondary=True)
			if not secondary_success:
				self.state,self.global_state = backup
				return False
		return True














	def respond_to_event(interface,event_description):
		pass


		