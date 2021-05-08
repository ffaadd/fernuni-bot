from discord.ext import commands
import inspect
import utils
import re
import discord
import collections

data = {"category": {"__none__": {"title": "Sonstiges", "description": ""}}, "command": {}}


def help_category(name=None, title=None, description=None):
    def decorator_help(cmd):
        data["category"][name] = {"title": title, "description": description}
        # if not data["category"][name]:
        #    data["category"][name] = {"description": description}
        # else:
        #    data["category"][name]["description"] = description
        return cmd

    return decorator_help

@help_category("help", "Hilfe", "Wenn du nicht weiter weißt, gib `!help` ein.")
def text_command_help(name, syntax=None, example=None, brief=None, description=None, mod=False, parameters={},
                      category=None):
    cmd = re.sub(r"^!", "", name)
    if syntax is None:
        syntax = name
    add_help(cmd, syntax, example, brief, description, mod, parameters, category)


def remove_help_for(name):
    data["command"].pop(name)


def help(syntax=None, example=None, brief=None, description=None, mod=False, parameters={}, category=None):
    def decorator_help(cmd):
        nonlocal syntax, parameters
        if syntax is None:
            arguments = inspect.signature(cmd.callback).parameters
            function_arguments = [
                f"<{item[1].name}{'?' if item[1].default != inspect._empty else ''}>" for item in
                list(arguments.items())[2:]]
            syntax = f"!{cmd.name} {' '.join(function_arguments)}"
        add_help(cmd.name, syntax, example, brief,
                 description, mod, parameters, category)
        return cmd

    return decorator_help


def add_help(cmd, syntax, example, brief, description, mod, parameters, category=None):
    if not category:
        category = "__none__"

    data["command"][cmd] = {
        "name": cmd,
        "syntax": syntax.strip(),
        "brief": brief,
        "example": example,
        "description": description,
        "parameters": parameters,
        "mod": mod,
        "category": category
    }


async def handle_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        # syntax = data[ctx.command.name]['syntax']
        # example = data[ctx.command.name]['example']

        msg = (
            f"Fehler! Du hast ein Argument vergessen. Für weitere Hilfe gib `!help {ctx.command.name}` ein. \n"
         f"`Syntax: {data['command'][ctx.command.name]['syntax']}`\n"
        )
        await ctx.channel.send(msg)
    else:
        raise error


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @help(
        category="help",
        brief="Zeigt die verfügbaren Kommandos an. Wenn ein Kommando übergeben wird, wird eine ausführliche Hilfe zu diesem Kommando angezeigt.",
    )
    @commands.command(name="help")
    async def cmd_help(self, ctx, command=None):
        if not command is None:
            command = re.sub(r"^!", "", command)
            await self.help_card(ctx, command)
            return
        await self.help_overview(ctx)

    @help(
        category="help",
        brief="Zeigt die verfügbaren Hilfe-Kategorien an.",
    )
    @commands.command(name="help-categories")
    @commands.check(utils.is_mod)
    async def cmd_categories(self, ctx):
        sorted_groups = {k: v for k, v in sorted(data["category"].items(), key=lambda item: item[1]['title'])}
        text = ""
        for key, value in sorted_groups.items():
            text += f"**{key} => {value['title']}**\n"
            text += f"- {value['description']}\n" if value['description'] else ""

        await ctx.channel.send(text)


    @help(
        category="help",
        brief="Zeigt die verfügbaren Kommandos *für Mods* an. Wenn ein Kommando übergeben wird, wird eine ausführliche Hilfe zu diesem Kommando angezeigt.",
        mod=True
    )
    @commands.command(name="mod-help")
    @commands.check(utils.is_mod)
    async def cmd_mod_help(self, ctx, command=None):
        if not command is None:
            command = re.sub(r"^!", "", command)
            await self.help_card(ctx, command)
            return
        await self.help_overview(ctx, True)

    async def help_overview(self, ctx, mod=False):
        sorted_groups = {k: v for k, v in sorted(data["category"].items(), key=lambda item: item[1]['title'])}
        sorted_commands = {k: v for k, v in sorted(data["command"].items(), key=lambda item: item[1]['syntax'])}

        title = "Boty hilft dir!"
        helptext = ("Um ausführliche Hilfe zu einem bestimmten Kommando zu erhalten, gib **!help <command>** ein. "
                    "Also z.B. **!help stats** um mehr über das Statistik-Kommando zu erfahren.\n\n")
        msgcount = 1

        for key, group in sorted_groups.items():
            text = f"\n__**{group['title']}**__\n"
            text += f"{group['description']}\n\n" if group['description'] else "\n"
            for command in sorted_commands.values():
                if command['mod'] != mod or command['category'] != key:
                    continue
                # {'*' if command['description'] else ''}\n"
                text += f"**{command['syntax']}**\n"
                text += f"{command['brief']}\n\n" if command['brief'] else "\n"
                if (len(helptext) + len(text) > 2048):
                    embed = discord.Embed(title=title,
                                          description=helptext,
                                          color=19607)
                    await utils.send_dm(ctx.author, "", embed=embed)
                    helptext = ""
                    msgcount = msgcount + 1
                    title = f"Boty hilft dir! (Fortsetzung {msgcount})"
                helptext += text
                text = ""

        embed = discord.Embed(title=title,
                              description=helptext,
                              color=19607)
        await utils.send_dm(ctx.author, "", embed=embed)

    async def help_card(self, ctx, name):
        try:
            command = data['command'][name]
            if command['mod'] and not utils.is_mod(ctx):
                raise KeyError
        except KeyError:
            await ctx.channel.send(
                "Fehler! Für dieses Kommando habe ich keinen Hilfe-Eintrag. Gib `!help` ein um eine Übersicht zu erhalten. ")
            return
        title = command['name']
        text = f"**{title}**\n"
        text += f"{command['brief']}\n\n" if command['brief'] else ""
        text += f"**Syntax:**\n `{command['syntax']}`\n"
        text += "**Parameter:**\n" if len(command['parameters']) > 0 else ""
        for param, desc in command['parameters'].items():
            text += f"`{param}` - {desc}\n"
        text += f"**Beispiel:**\n `{command['example']}`\n" if command['example'] else ""
        text += f"\n{command['description']}\n" if command['description'] else ""
        embed = discord.Embed(title=title,
                              description=text,
                              color=19607)
        await utils.send_dm(ctx.author, text)  # , embed=embed)

    @commands.command(name="all-help")
    @commands.check(utils.is_mod)
    async def help_all(self, ctx, mod=False):
        sorted_groups = {k: v for k, v in sorted(data["category"].items(), key=lambda item: item[1]['title'])}
        sorted_commands = {k: v for k, v in sorted(data["command"].items(), key=lambda item: item[1]['syntax'])}
        title = "Boty hilft dir!"
        helptext = ("Um ausführliche Hilfe zu einem bestimmten Kommando zu erhalten, gib **!help <command>** ein. "
                    "Also z.B. **!help stats** um mehr über das Statistik-Kommando zu erfahren.\n\n\n")
        msgcount = 1
        for key, group in sorted_groups.items():
            text = f"\n__**{group['title']}**__\n"
            text += f"{group['description']}\n\n" if group['description'] else "\n"
            for command in sorted_commands.values():
                if command['category'] != key:
                    continue
                text += f"**{command['name']}**{' (mods only)' if command['mod'] else ''}\n"
                text += f"{command['brief']}\n\n" if command['brief'] else ""
                text += f"**Syntax:**\n `{command['syntax']}`\n"
                text += "**Parameter:**\n" if len(
                    command['parameters']) > 0 else ""
                for param, desc in command['parameters'].items():
                    text += f"`{param}` - {desc}\n"
                text += f"**Beispiel:**\n `{command['example']}`\n" if command['example'] else ""
                text += f"\n{command['description']}\n" if command['description'] else ""
                text += "=====================================================\n"
                if (len(helptext) + len(text) > 2048):
                    embed = discord.Embed(title=title,
                                          description=helptext,
                                          color=19607)
                    await utils.send_dm(ctx.author, "", embed=embed)
                    helptext = ""
                    msgcount = msgcount + 1
                    title = f"Boty hilft dir! (Fortsetzung {msgcount})"
                helptext += text
                text = ""

        embed = discord.Embed(title=title,
                              description=helptext,
                              color=19607)
        await utils.send_dm(ctx.author, "", embed=embed)
