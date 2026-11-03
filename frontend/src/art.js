const ICONS={
 user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
 globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>',
 card:'<rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M2.5 10h19M6 15h4"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 key:'<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/>',
 plane:'<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
 check:'<path d="M5 12.5l4.5 4.5L19 7"/>',
 home:'<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
 inbox:'<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z"/>',
 users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-5.5 6.5-5.5s6.5 2 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5c2 .6 3.5 2.3 3.5 5.5"/>',
 ticket:'<path d="M3 8a2 2 0 0 0 0 4 2 2 0 0 1 0 4v2h18v-2a2 2 0 0 1 0-4 2 2 0 0 0 0-4V6H3z"/><path d="M14 6v12" stroke-dasharray="2 2"/>',
 calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
 mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
 settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
 pin:'<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
 sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'
};
const ico=(n,sz)=>`<svg class="ico" width="${sz||18}" height="${sz||18}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${ICONS[n]||''}</svg>`;
function scene(id){
  return `<svg class="scene" viewBox="0 0 800 360" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
  <defs><linearGradient id="sea${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a9ad6"/><stop offset="1" stop-color="#1b6aa0"/></linearGradient></defs>
  <circle cx="640" cy="92" r="46" fill="#f7a23c" opacity=".95"/><circle cx="640" cy="92" r="70" fill="#f7a23c" opacity=".18"/>
  <g fill="#fff" opacity=".85"><ellipse cx="170" cy="80" rx="46" ry="13"/><ellipse cx="205" cy="70" rx="30" ry="14"/><ellipse cx="480" cy="54" rx="36" ry="10"/><ellipse cx="505" cy="47" rx="22" ry="10"/></g>
  <path d="M60 170 C 220 70, 420 60, 560 120" fill="none" stroke="#fff" stroke-width="2.5" stroke-dasharray="7 9" opacity=".75"/>
  <g transform="translate(560 120) rotate(22) scale(1.5)" fill="#fff"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z" transform="translate(-12 -12)"/></g>
  <path d="M0 250 L120 170 L190 215 L300 130 L420 225 L500 180 L620 240 L700 200 L800 235 V360 H0z" fill="#0f4f7c" opacity=".55"/>
  <path d="M0 268 L90 228 L180 255 L260 210 L360 262 L470 226 L560 266 L680 232 L800 262 V360 H0z" fill="#0d3f63" opacity=".7"/>
  <rect x="0" y="282" width="800" height="78" fill="url(#sea${id})"/>
  <path d="M0 290 q25 -8 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0" fill="none" stroke="#bfe3fa" stroke-width="2" opacity=".7"/>
  <path d="M30 318 q25 -7 50 0 t50 0 t50 0 M330 330 q25 -7 50 0 t50 0 t50 0 M600 314 q25 -7 50 0 t50 0" fill="none" stroke="#bfe3fa" stroke-width="2" opacity=".45"/>
  <g transform="translate(420 262)"><path d="M0 26 h56 l-8 10 h-40z" fill="#fff"/><path d="M26 24 V-12 L50 22z" fill="#f07c1b"/><path d="M24 24 V-4 L6 22z" fill="#fff" opacity=".9"/></g>
  </svg>`;
}

function sceneW(id){
  return `<svg class="scene" viewBox="0 0 1200 300" preserveAspectRatio="xMaxYMax slice" aria-hidden="true">
  <defs><linearGradient id="sw${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a9ad6"/><stop offset="1" stop-color="#1b6aa0"/></linearGradient></defs>
  <circle cx="1040" cy="78" r="38" fill="#f7a23c"/><circle cx="1040" cy="78" r="60" fill="#f7a23c" opacity=".18"/>
  <g fill="#fff" opacity=".8"><ellipse cx="760" cy="62" rx="40" ry="11"/><ellipse cx="790" cy="54" rx="24" ry="11"/><ellipse cx="1130" cy="140" rx="34" ry="9"/></g>
  <path d="M560 150 C 700 60, 840 50, 930 92" fill="none" stroke="#fff" stroke-width="2.5" stroke-dasharray="7 9" opacity=".7"/>
  <g transform="translate(936 94) rotate(25) scale(1.3)" fill="#fff"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z" transform="translate(-12 -12)"/></g>
  <path d="M520 240 L640 178 L720 212 L830 150 L940 214 L1020 186 L1110 222 L1200 196 V300 H520z" fill="#0f4f7c" opacity=".45"/>
  <path d="M480 252 L600 222 L700 246 L790 214 L900 250 L1010 224 L1100 250 L1200 232 V300 H480z" fill="#0d3f63" opacity=".55"/>
  <rect x="0" y="262" width="1200" height="38" fill="url(#sw${id})" opacity=".9"/>
  <path d="M0 268 q25 -7 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0" fill="none" stroke="#bfe3fa" stroke-width="2" opacity=".6"/>
  <g transform="translate(860 238) scale(.8)"><path d="M0 26 h56 l-8 10 h-40z" fill="#fff"/><path d="M26 24 V-12 L50 22z" fill="#f07c1b"/><path d="M24 24 V-4 L6 22z" fill="#fff" opacity=".9"/></g>
  </svg>`;
}
export {ICONS, ico, scene, sceneW};
