// New isolated, original miniature 3D-style RDC EuroNight locomotive front marker.
// All original Stockholm Rail icons and their dimensions remain byte-for-byte intact.
// This is illustrative artwork; real locomotive photo shown separately in the detail panel.
const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
<defs>
 <linearGradient id="roof" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#b9b6b1"/><stop offset=".43" stop-color="#f3f1ec"/><stop offset="1" stop-color="#827d78"/></linearGradient>
 <linearGradient id="nose" x1="0" y1="0" x2=".9" y2="1"><stop stop-color="#827eac"/><stop offset=".42" stop-color="#4f457b"/><stop offset=".8" stop-color="#2f3055"/><stop offset="1" stop-color="#1e2346"/></linearGradient>
 <linearGradient id="side" x1="0" y1="0" x2="1" y2=".7"><stop stop-color="#d9d4c9"/><stop offset=".55" stop-color="#a8a9a6"/><stop offset="1" stop-color="#6b7477"/></linearGradient>
 <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#152a30"/><stop offset=".4" stop-color="#354b54"/><stop offset="1" stop-color="#071c21"/></linearGradient>
</defs>
<ellipse cx="24" cy="42" rx="17.6" ry="3.5" fill="#14282a" opacity=".20"/>
<path d="M16 6 L37 10 Q41 11 43 16 L44 31 L29 39 L15 37Z" fill="url(#side)" stroke="#646c70" stroke-width=".5"/>
<path d="M16 6 L37 10 Q40 11 43 16 L32 15 L12 11Z" fill="url(#roof)" stroke="#817e79" stroke-width=".7"/>
<path d="M31 16 L42 18 L42 29 L30 35Z" fill="#929b9d" stroke="#5c666b" stroke-width=".65"/>
<path d="M34 18 L40 20 L40 25 L34 27Z" fill="#273e45" stroke="#c5cbc8" stroke-width=".8"/>
<path d="M32 27 L41 27 L41 29 L31 34Z" fill="#413969"/>
<path d="M8 13 Q10 9 15 10 L31 15 L31 34 Q26 42 15 42 Q9 40 7 34 L7 19Z" fill="url(#nose)" stroke="#332b5c" stroke-width=".75"/>
<path d="M9 19 L10 15 Q12 13 15 13 L28 17 L28 27 L9 26Z" fill="url(#glass)" stroke="#101f27" stroke-width=".85"/>
<path d="M11 17 L14 15 L18 16 L14 25 L10 24Z" fill="#8eafb5" opacity=".38"/>
<path d="M20 17 L26 19 L26 23 L20 26Z" fill="#a3c0c4" opacity=".13"/>
<path d="M9 29 L28 31 L27 36 Q19 41 11 36Z" fill="#554e86"/>
<path d="M10 34 Q20 39 28 34 L26 39 Q18 43 12 38Z" fill="#373c40" stroke="#727779" stroke-width=".5"/>
<path d="M14 39 L22 39 L22 42 L14 42Z" fill="#35383b"/>
<path d="M15 41 L21 41 L21 44 L15 44Z" fill="#212a2e"/>
<path d="M12 30 L15 31 L15 33 L12 33Z" fill="#fff1bb" stroke="#f9da8a" stroke-width=".6"/>
<path d="M24 31 L27 31 L27 34 L24 34Z" fill="#fff1bb" stroke="#f9da8a" stroke-width=".6"/>
<path d="M15 12 L23 14" stroke="#f4eee4" stroke-width="1" opacity=".8"/>
<path d="M8 21 L8 32" stroke="#c9c5e2" stroke-width=".65" opacity=".8"/>
<path d="M43 17 L43 29" stroke="#e5e5e0" stroke-width=".6" opacity=".75"/>
</svg>`;
export const rdcMarker='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
