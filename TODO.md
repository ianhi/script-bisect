
## Styling

If we fail to find a bad commit we still report success:

```
    ✅ Good
  ✨ Bisection complete! ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

⚠️ Could not find a clear first bad commit

✨ Bisection completed successfully!
```

Commit success or failure should be on the same line as the commit message (replacing the magnifiying glass)

    ✅ Good
  🔍 Testing commit ef180b8eeca3 (Add DataTree.prune() method … (#10598))
    ✅ Good
  🔍 Testing commit 44d5fd69d39f (Fix `ds.merge` to prevent altering original object depending on join
value (#10596))
    ✅ Good

## UI

Continue with edited script. should show the script, and give the option to go back to editing

## Cloning

We already get tags for the autocomplete, but then once we start the process we do a shallow clone. this seems redundant. Let's make sure instead of a shallow clone we are doing fetching rev log without the blobs

Initially during bisect there are weird logging outputs:

🔍 Auto-detecting repository URL...
⠋ Cloning repository (shallow)...[17:34:32] INFO     Shallow cloning <https://github.com/pydata/xarray.git> to             bisector.py:146
                    /var/folders/tc/fkgp35zn7z913f9cmsxcl6pc0000gn/T/script_bisect_repo
                    _jen2ig7b
⠼ ✅ Repository ready for bisection

we should not have those for a consistent visual style

## Error Display

Simplify the error display to the user - it should only show one line with the actual error message instead of full stack traces and multiple lines of debug output.

## Agent instructions - HARD

add a flag for --agent that explains to an LLM how to use this tool and how to update the script appropriately (i.e. with exit code) so that it reproduces the issue.

Or even better we can have script-bisect --agent <link> have the agent automatically interpret the issue and modify the script to have the correct exit status and then using the script-bisect tool itself. This will require prompting the user for what agent command (maybe autodetecting? and passing the ocmmon on to them)
