from Elapsed.core.bot import Anony
from Elapsed.core.dir import dirr
from Elapsed.core.git import git
from Elapsed.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = Anony()
