"""Shared source-aware diagnostic rendering; JSON remains the stable default."""
from pathlib import Path


def human(report):
    result=[]
    for item in report.get('errors',[]):
        file=item.get('file','');line,column=item.get('pos',(1,1));line=max(1,line);column=max(1,column)
        result.append(f'{file+":" if file else ""}{line}:{column}: error[{item.get("kind","check")}]: {item.get("msg","")}')
        if file:
            try:
                text=Path(file).read_text().splitlines()[line-1]
                result.append('  '+text);result.append('  '+' '*len(text[:column-1].expandtabs(2))+'^')
            except (OSError,IndexError,UnicodeError):pass
    if not result:
        result.append('neo: check passed' if report.get('ok') else 'neo: '+report.get('error','check failed'))
        for obligation in report.get('obligations',[]):
            if obligation.get('status') in ('unknown','unproven'):result.append('  '+str(obligation))
    return '\n'.join(result)
