const fs = require('fs');
const path = require('path');

const handlerPath = path.join(__dirname, '..', '.open-next', 'server-functions', 'default', 'handler.mjs');

if (fs.existsSync(handlerPath)) {
  let content = fs.readFileSync(handlerPath, 'utf8');
  let patched = false;

  // Replace dynamic require of fs/path in file-logger
  const target = 'var _fs=_interop_require_default(require("fs")),_path=_interop_require_default(require("path"));';
  const replacement = 'var _fs={default:{mkdirSync(){},writeFileSync(){}}},_path={default:{join(...a){return a.join("/")},dirname(p){return p}}};';

  if (content.includes(target)) {
    content = content.replace(target, replacement);
    patched = true;
  }

  // Also replace the dynamic require stub so any other unexpected dynamic require of Node core modules returns a safe stub rather than throwing at top-level
  const stubTarget = "throw Error('Dynamic require of \"'+x+'\" is not supported')";
  const stubReplacement = 'if(x==="fs"||x==="node:fs"||x==="path"||x==="node:path")return {};throw Error(\'Dynamic require of "\'+x+\'" is not supported\')';

  if (content.includes(stubTarget)) {
    content = content.replace(stubTarget, stubReplacement);
    patched = true;
  }

  if (patched) {
    fs.writeFileSync(handlerPath, content, 'utf8');
    console.log('Successfully patched handler.mjs');
  } else {
    console.log('No patches needed or patterns not found');
  }
} else {
  console.log('handler.mjs does not exist yet');
}
