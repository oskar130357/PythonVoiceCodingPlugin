import os
import sys

import sublime
import sublime_plugin


# making sure our dependencies are in the path
sys.path.insert(0,os.path.join(os.path.dirname(__file__), 'third_party'))

from PythonVoiceCodingPlugin.interface.interface import Interface


PLUGIN_VERSION = (0,1,2)

settings = {}
already_message = False	

def plugin_loaded():
	global settings
	settings = sublime.load_settings("python_voice_coding_plugin.sublime-settings")
	try : 
		from package_control import events
		if events.post_upgrade("PythonVoiceCodingPlugin"):
			sublime.error_message(
"""
CRITICAL UPDATE PythonVoiceCodingPlugin
Up to release 0.1.1 a subtle yet critical installation step regarding communication between sublime and Caster was not documented, which may have prevented you from using the plug-in altogether! 

You can find more information at https://github.com/mpourmpoulis/PythonVoiceCodingPlugin/issues/15 but simply upgrading your Caster grammar should be enough!
For Caster 1.x.x users Preferences > Package Settings  > PythonVoiceCodingPlugin >Quick 1.0.0 Install may make these process faster!

My sincerest apologies!
""")
	except :
		pass



class PythonVoiceCodingPluginCommand(sublime_plugin.TextCommand):
	def run(self, edit,arg):
		global already_message
		if "grammar_version" not in arg  and not already_message:
			sublime.error_message("You are using main plug-in version >=0.1.0 with a grammar <= 0.0.5." + 
				"They are not compatible." + 
				"You can find the new newest version of the grammar along with instructions to install it\n" + 
				" Under  Preferences > Package Settings > PythonVoiceCodingPlugin"

			)
			already_message = True
		self.action_one(edit,arg)

	def action_one(self, edit,arg):
		global settings
		interface = Interface(
			sublime = sublime,
			view = self.view,
			window = sublime.active_window(),
			edit = edit,
			settings = settings
		)
		interface.respond_to_query(arg)
		interface.respond_to_event({"event":"update_change_count","change_count":self.view.change_count()})







