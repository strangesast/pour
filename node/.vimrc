set secure

set textwidth=80
set wildignore+=*.swp,*/lib/*.js,*.original
let g:ctrlp_working_path_mode = 0 " uses git root (parent directory) by default
noremap <C-p> :CtrlP ./ <CR>
