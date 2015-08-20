'''

'''
from __future__ import division
__author__ = 'sivanov'

list0 = u'{} list:\n'
list_er0 =  u"There is no tasks in {} list!\nExample:\n/list \n /list @Jack"

done0 = u"I'm pleased to claim that you finished {0}!"
done_er0 = u"Please, specify correct task.\nExample:\n/done 1\n/done @Jack 1,2"
done1 = u"I removed {} list."

todo0 = u'Saved {0} to {1} list'
todo_er0 = u'Please specify task.\nExample:\n /todo Buy milk\n/todo @Jack Call to insurance'

help0 = u''' This is a Telegram ToDo bot.

        Write /help - to get this message.
        Write /todo task - to write another task. You can provide multiple tasks, where each task in a new line.
        Write /list - to list current tasks in your ToDo list.
        Write /done task1, task2, ... - to finish the task.
        Write /completed - to list completed tasks in your ToDo list. (new)

        Having more ideas or want to contribute? Write a comment to http://storebot.me/bot/todobbot.
        '''

completed0 = u'Completed tasks:\n{0}\n*All dates are UTC.'
completed_er0 = u"You have no finished tasks!"

tutorial0 = u"""
Hi {0}! {1}
Let's start a 1-minute tutorial.
First things first, let's create your first task.
Type "/todo Make my day!"
"""

tutorial1 = u"""

Great! {0} Let's see what tasks you have in your list.
Type "/list" to show created tasks.
"""

tutorial2 = u"""

You rock! {0} Now, let's mark the first task as done.
Type "/done 1" to complete the task.
"""

tutorial3 = u"""

That was awesome! {0} Of course, you can see all completed tasks.
Type "/completed" to view all completed tasks.
"""

tutorial4 = u"""

{2} Perfect, you're almost set!
You can now add me to one of your group chats, so all its members can never forget a thing.

And a few more hints:
{0} If the word after /todo or /list or /done starts with @, it will manage a named list.
 For example, /todo @Jack Buy milk -- will create a task in Jack's list.
{1} You can autocomplete commands with TAB key. It's just convenient!

We welcome you to our friendly community!
P.S. Have troubles? Write us /feedback.
"""

tutorial_er0 = u'Something went wrong. Please, type "/todo My first task".'
tutorial_er1 = u'Something went wrong. Please, type "/list".'
tutorial_er2 = u'Something went wrong. Please, type "/done 1"'
tutorial_er3 = u'Something went wrong. Please, type "/completed".'

feedback0 = u"Please, write a feedback at thetodobot.com."




if __name__ == "__main__":
    console = []