import asyncio
import os
import sys

import heroku3
import urllib3
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from userbot.helpers import runner

from . import *

HEROKU_APP_NAME = Config.HEROKU_APP_NAME or None
HEROKU_API_KEY = Config.HEROKU_API_KEY or None
Heroku = heroku3.from_key(Config.HEROKU_API_KEY)
heroku_api = "https://api.heroku.com"

UPSTREAM_REPO_BRANCH = "ANdencento"

UPSTREAM_REPO_URL = "https://github.com/Andencento/Deploy-Andencento"

REPO_REMOTE_NAME = "temponame"
IFFUCI_ACTIVE_BRANCH_NAME = "ANdencento"
NO_HEROKU_APP_CFGD = "No Heroku App Found!"
HEROKU_GIT_REF_SPEC = "HEAD:refs/heads/master"
RESTARTING_APP = "Restarting Heroku App..."
IS_SELECTED_DIFFERENT_BRANCH = (
    "looks like a custom branch {branch_name} "
    "is being used:\n"
    "in this case, Updater is unable to identify the branch to be updated."
    "please check out to an official branch, and re-start the updater."
)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

requirements_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "requirements.txt"
)


async def gen_chlog(repo, diff):
    d_form = "%d/%m/%y"
    return "".join(
        f"  • {c.summary} ({c.committed_datetime.strftime(d_form)}) <{c.author}>\n"
        for c in repo.iter_commits(diff)
    )


async def print_changelogs(event, ac_br, changelog):
    changelog_str = (
        f"🔥 **New UPDATE available for [{ac_br}]:\n\n📑 CHANGELOG:**\n`{changelog}`"
    )
    if len(changelog_str) > 4096:
        await event.edit("`Changelog is too big, view the file to see it.`")
        with open("output.txt", "w+") as file:
            file.write(changelog_str)
        await event.client.send_file(
            event.chat_id,
            "output.txt",
            reply_to=event.id,
            thumb=user_logo,
        )
        os.remove("output.txt")
    else:
        await event.client.send_message(
            event.chat_id,
            changelog_str,
            reply_to=event.id,
        )
    return True


async def update_requirements():
    reqs = str(requirements_path)
    try:
        process = await asyncio.create_subprocess_suser(
            " ".join([sys.executable, "-m", "pip", "install", "-r", reqs]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        return process.returncode
    except Exception as e:
        return repr(e)


async def update(event, repo, ups_rem, ac_br):
    try:
        ups_rem.pull(ac_br)
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")
    await update_requirements()
    await event.edit(
        "✅ Successfully updated Aɴᴅᴇɴᴄᴇɴᴛᴏ!\n\nBot is restarting please wait for a minute."
    )
    args = [sys.executable, "-m", "userbot"]
    os.execle(sys.executable, *args, os.environ)
    return


async def deploy(event, repo, ups_rem, ac_br, txt):
    if HEROKU_API_KEY is not None:
        heroku = heroku3.from_key(HEROKU_API_KEY)
        heroku_app = None
        heroku_applications = heroku.apps()
        if HEROKU_APP_NAME is None:
            await event.edit("**Please set up**  `HEROKU_APP_NAME`  **to update!")
            repo.__del__()
            return
        for app in heroku_applications:
            if app.name == HEROKU_APP_NAME:
                heroku_app = app
                break
        if heroku_app is None:
            await event.edit(f"{txt}\n" "`Invalid Heroku vars for updating.")
            return repo.__del__()
        await event.edit("`Updating Userbot In Progress...Please wait upto 5 minutes.`")
        ups_rem.fetch(ac_br)
        repo.git.reset("--hard", "FETCH_HEAD")
        heroku_git_url = heroku_app.git_url.replace(
            "https://", "https://api:" + HEROKU_API_KEY + "@"
        )
        if "heroku" in repo.remotes:
            remote = repo.remote("heroku")
            remote.set_url(heroku_git_url)
        else:
            remote = repo.create_remote("heroku", heroku_git_url)
        try:
            remote.push(refspec="HEAD:refs/heads/master", force=True)
        except Exception as error:
            await event.edit(f"{txt}\n**Error log:**\n`{error}`")
            return repo.__del__()
        build_status = app.builds(order_by="created_at", sort="desc")[0]
        if build_status.status == "failed":
            await event.edit("`Build failed ⚠️`")
            await asyncio.sleep(5)
            return await event.delete()
        await event.edit(
            f"**Your ᴀɴᴅᴇɴᴄᴇɴᴛᴏ Is UpToDate**\n\n**Version :**  __{user_ver}__\n**Oɯɳҽɾ :**  {user_mention}"
        )
    else:
        await event.edit(
            "**Please set up**  `HEROKU_API_KEY`  **from heroku to update!**"
        )
    return


@Andencento.on(andencento_cmd(outgoing=True, pattern=r"update build$"))
@Andencento.on(sudo_cmd(pattern="update build$", allow_sudo=True))
async def upstream(event):
    event = await edit_or_reply(
        event,
        "`Hard-Update In Progress... \nPlease wait until docker build is finished...`",
    )
    off_repo = "https://github.com/Andencento/Deploy-Andencento"
    os.chdir("/app")
    git_user = f"rm -rf .git"
    try:
        await runner.runcmd(git_user)
    except BaseException:
        pass
    try:
        txt = "😕 `Updater cannot continue due to some problems occured`\n\n**LOGTRACE:**\n"
        repo = Repo()
    except NoSuchPathError as error:
        await event.edit(f"{txt}\n`directory {error}  not found`")
        return repo.__del__()
    except GitCommandError as error:
        await event.edit(f"{txt}\n`Early failure! {error}`")
        return repo.__del__()
    except InvalidGitRepositoryError:
        repo = Repo.init()
        origin = repo.create_remote("upstream", off_repo)
        origin.fetch()
        repo.create_head("ANdencento", origin.refs.ANdencento)
        repo.heads.ANdencento.set_tracking_branch(origin.refs.ANdencento)
        repo.heads.ANdencento.checkout(True)
    try:
        repo.create_remote("upstream", off_repo)
    except BaseException:
        pass
    ac_br = repo.active_branch.name
    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)
    await event.edit(
        f"**Aɴᴅᴇɴᴄᴇɴᴛᴏ Docker Build In Progress... Type** `{hl}ping`  **after 5 mins to check if Bot is working!**"
    )
    await deploy(event, repo, ups_rem, ac_br, txt)


CmdHelp("update").add_command(
    "update", None, "Checks if any new update is available."
).add_command(
    "update now",
    None,
    "Soft-Update Your Aɴᴅᴇɴᴄᴇɴᴛᴏ. Basically if you restart dyno it will go back to previous deploy.",
).add_command(
    "update build",
    None,
    "Hard-Update Your Aɴᴅᴇɴᴄᴇɴᴛᴏ. This won't take you back to your previous deploy. This will be triggered even if there is no changelog.",
).add_info(
    "Aɴᴅᴇɴᴄᴇɴᴛᴏ Updater."
).add_warning(
    "✅ Harmless Module."
).add()
