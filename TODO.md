
## Styling

Commit success or failure should be on the same line as the commit message (replacing the magnifiying glass)

    ✅ Good
  🔍 Testing commit ef180b8eeca3 (Add DataTree.prune() method … (#10598))
    ✅ Good
  🔍 Testing commit 44d5fd69d39f (Fix `ds.merge` to prevent altering original object depending on join
value (#10596))
    ✅ Good

## Error Display

Simplify the error display to the user - it should only show one line with the actual error message instead of full stack traces and multiple lines of debug output.

## Output

There are too many outputs making it hard to parse

## Progress bar display issue

When auto-adding dependencies, the progress bar display gets broken up by console.print statements from dependency fixing. The progress bar shows multiple lines mixed with dependency detection messages, which breaks the visual continuity of the progress display.

## Add flag for complete error tracebacks

Add a `--full-traceback` or `--debug-errors` flag to show complete error tracebacks instead of the simplified one-line error summaries. This would be useful for debugging when the simplified error message isn't sufficient.

## simplify UI interactions

especially when requesting an issue from github there are redundant confirmation dialogs. for example after choosing a code block it asks again to confirm that we want to use that code block. we should eliminate that step. Also at the point of confirming the bisection we should have clearly indicated keybindings for editing the refs, the script or even what package we are bisecting.

## End State

at the end of a run sometimes it's not satistfying because the user had a bad script, or they used the wrong refs. if they had to edit the script to make it work then this is very annoying. We should consider having an option at the end to re-run with different parameters. also if the command is run again with the same input (e.g. same github issue we should cache that and ask the user if they want to use the same script as before)

## Agent instructions - HARD

add a flag for --agent that explains to an LLM how to use this tool and how to update the script appropriately (i.e. with exit code) so that it reproduces the issue.

Or even better we can have script-bisect --agent <link> have the agent automatically interpret the issue and modify the script to have the correct exit status and then using the script-bisect tool itself. This will require prompting the user for what agent command (maybe autodetecting? and passing the ocmmon on to them)
