!function(t){var e={};function n(i){if(e[i])return e[i].exports;var s=e[i]={i:i,l:!1,exports:{}};return t[i].call(s.exports,s,s.exports,n),s.l=!0,s.exports}n.m=t,n.c=e,n.d=function(t,e,i){n.o(t,e)||Object.defineProperty(t,e,{enumerable:!0,get:i})},n.r=function(t){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(t,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(t,"__esModule",{value:!0})},n.t=function(t,e){if(1&e&&(t=n(t)),8&e)return t;if(4&e&&"object"==typeof t&&t&&t.__esModule)return t;var i=Object.create(null);if(n.r(i),Object.defineProperty(i,"default",{enumerable:!0,value:t}),2&e&&"string"!=typeof t)for(var s in t)n.d(i,s,function(e){return t[e]}.bind(null,s));return i},n.n=function(t){var e=t&&t.__esModule?function(){return t.default}:function(){return t};return n.d(e,"a",e),e},n.o=function(t,e){return Object.prototype.hasOwnProperty.call(t,e)},n.p="/newres/",n(n.s=34)}([function(t,e,n){"use strict";var i=n(3);class s{handleAttributeExpressions(t,e,n,s){const r=e[0];return"."===r?new i.f(t,e.slice(1),n).parts:"@"===r?[new i.d(t,e.slice(1),s.eventContext)]:"?"===r?[new i.c(t,e.slice(1),n)]:new i.a(t,e,n).parts}handleTextExpression(t){return new i.e(t)}}const r=new s;var o=n(11),a=n(9),c=n(5),l=n(4),u=n(1);function h(t){let e=d.get(t.type);void 0===e&&(e={stringsArray:new WeakMap,keyString:new Map},d.set(t.type,e));let n=e.stringsArray.get(t.strings);if(void 0!==n)return n;const i=t.strings.join(u.f);return void 0===(n=e.keyString.get(i))&&(n=new u.a(t,t.getTemplateElement()),e.keyString.set(i,n)),e.stringsArray.set(t.strings,n),n}const d=new Map,p=new WeakMap,f=(t,e,n)=>{let s=p.get(e);void 0===s&&(Object(c.b)(e,e.firstChild),p.set(e,s=new i.e(Object.assign({templateFactory:h},n))),s.appendInto(e)),s.setValue(t),s.commit()};var m=n(14);n.d(e,"c",function(){return _}),n.d(e,!1,function(){return s}),n.d(e,!1,function(){return r}),n.d(e,"b",function(){return a.a}),n.d(e,!1,function(){return a.b}),n.d(e,!1,function(){return c.b}),n.d(e,!1,function(){return c.c}),n.d(e,!1,function(){return l.a}),n.d(e,!1,function(){return l.b}),n.d(e,!1,function(){return i.a}),n.d(e,"a",function(){return i.b}),n.d(e,!1,function(){return i.c}),n.d(e,!1,function(){return i.d}),n.d(e,!1,function(){return i.g}),n.d(e,!1,function(){return i.e}),n.d(e,!1,function(){return i.f}),n.d(e,!1,function(){}),n.d(e,!1,function(){return p}),n.d(e,"d",function(){return f}),n.d(e,!1,function(){return d}),n.d(e,!1,function(){return h}),n.d(e,!1,function(){return m.a}),n.d(e,!1,function(){return o.a}),n.d(e,!1,function(){return o.b}),n.d(e,!1,function(){return u.c}),n.d(e,!1,function(){return u.d}),n.d(e,!1,function(){return u.a});const _=(t,...e)=>new o.b(t,e,"html",r)},function(t,e,n){"use strict";n.d(e,"f",function(){return i}),n.d(e,"g",function(){return s}),n.d(e,"b",function(){return o}),n.d(e,"a",function(){return a}),n.d(e,"d",function(){return c}),n.d(e,"c",function(){return l}),n.d(e,"e",function(){return u});const i=`{{lit-${String(Math.random()).slice(2)}}}`,s=`\x3c!--${i}--\x3e`,r=new RegExp(`${i}|${s}`),o="$lit$";class a{constructor(t,e){this.parts=[],this.element=e;let n=-1,s=0;const a=[],c=e=>{const h=e.content,d=document.createTreeWalker(h,133,null,!1);let p=0;for(;d.nextNode();){n++;const e=d.currentNode;if(1===e.nodeType){if(e.hasAttributes()){const a=e.attributes;let c=0;for(let t=0;t<a.length;t++)a[t].value.indexOf(i)>=0&&c++;for(;c-- >0;){const i=t.strings[s],a=u.exec(i)[2],c=a.toLowerCase()+o,l=e.getAttribute(c).split(r);this.parts.push({type:"attribute",index:n,name:a,strings:l}),e.removeAttribute(c),s+=l.length-1}}"TEMPLATE"===e.tagName&&c(e)}else if(3===e.nodeType){const t=e.data;if(t.indexOf(i)>=0){const i=e.parentNode,o=t.split(r),c=o.length-1;for(let t=0;t<c;t++)i.insertBefore(""===o[t]?l():document.createTextNode(o[t]),e),this.parts.push({type:"node",index:++n});""===o[c]?(i.insertBefore(l(),e),a.push(e)):e.data=o[c],s+=c}}else if(8===e.nodeType)if(e.data===i){const t=e.parentNode;null!==e.previousSibling&&n!==p||(n++,t.insertBefore(l(),e)),p=n,this.parts.push({type:"node",index:n}),null===e.nextSibling?e.data="":(a.push(e),n--),s++}else{let t=-1;for(;-1!==(t=e.data.indexOf(i,t+1));)this.parts.push({type:"node",index:-1})}}};c(e);for(const t of a)t.parentNode.removeChild(t)}}const c=t=>-1!==t.index,l=()=>document.createComment(""),u=/([ \x09\x0a\x0c\x0d])([^\0-\x1F\x7F-\x9F \x09\x0a\x0c\x0d"'>=/]+)([ \x09\x0a\x0c\x0d]*=[ \x09\x0a\x0c\x0d]*(?:[^ \x09\x0a\x0c\x0d"'`<>=]*|"[^"]*|'[^']*))$/},function(t,e,n){"use strict";function i(t,e){if(t.hasOwnProperty(e)){let n=t[e];delete t[e],t[e]=n}}n.d(e,"a",function(){return i})},function(t,e,n){"use strict";n.d(e,"g",function(){return l}),n.d(e,"a",function(){return u}),n.d(e,"b",function(){return h}),n.d(e,"e",function(){return d}),n.d(e,"c",function(){return p}),n.d(e,"f",function(){return f}),n.d(e,"d",function(){return g});var i=n(9),s=n(5),r=n(4),o=n(14),a=n(11),c=n(1);const l=t=>null===t||!("object"==typeof t||"function"==typeof t);class u{constructor(t,e,n){this.dirty=!0,this.element=t,this.name=e,this.strings=n,this.parts=[];for(let t=0;t<n.length-1;t++)this.parts[t]=this._createPart()}_createPart(){return new h(this)}_getValue(){const t=this.strings,e=t.length-1;let n="";for(let i=0;i<e;i++){n+=t[i];const e=this.parts[i];if(void 0!==e){const t=e.value;if(null!=t&&(Array.isArray(t)||"string"!=typeof t&&t[Symbol.iterator]))for(const e of t)n+="string"==typeof e?e:String(e);else n+="string"==typeof t?t:String(t)}}return n+t[e]}commit(){this.dirty&&(this.dirty=!1,this.element.setAttribute(this.name,this._getValue()))}}class h{constructor(t){this.value=void 0,this.committer=t}setValue(t){t===r.a||l(t)&&t===this.value||(this.value=t,Object(i.b)(t)||(this.committer.dirty=!0))}commit(){for(;Object(i.b)(this.value);){const t=this.value;this.value=r.a,t(this)}this.value!==r.a&&this.committer.commit()}}class d{constructor(t){this.value=void 0,this._pendingValue=void 0,this.options=t}appendInto(t){this.startNode=t.appendChild(Object(c.c)()),this.endNode=t.appendChild(Object(c.c)())}insertAfterNode(t){this.startNode=t,this.endNode=t.nextSibling}appendIntoPart(t){t._insert(this.startNode=Object(c.c)()),t._insert(this.endNode=Object(c.c)())}insertAfterPart(t){t._insert(this.startNode=Object(c.c)()),this.endNode=t.endNode,t.endNode=this.startNode}setValue(t){this._pendingValue=t}commit(){for(;Object(i.b)(this._pendingValue);){const t=this._pendingValue;this._pendingValue=r.a,t(this)}const t=this._pendingValue;t!==r.a&&(l(t)?t!==this.value&&this._commitText(t):t instanceof a.b?this._commitTemplateResult(t):t instanceof Node?this._commitNode(t):Array.isArray(t)||t[Symbol.iterator]?this._commitIterable(t):t===r.b?(this.value=r.b,this.clear()):this._commitText(t))}_insert(t){this.endNode.parentNode.insertBefore(t,this.endNode)}_commitNode(t){this.value!==t&&(this.clear(),this._insert(t),this.value=t)}_commitText(t){const e=this.startNode.nextSibling;t=null==t?"":t,e===this.endNode.previousSibling&&3===e.nodeType?e.data=t:this._commitNode(document.createTextNode("string"==typeof t?t:String(t))),this.value=t}_commitTemplateResult(t){const e=this.options.templateFactory(t);if(this.value&&this.value.template===e)this.value.update(t.values);else{const n=new o.a(e,t.processor,this.options),i=n._clone();n.update(t.values),this._commitNode(i),this.value=n}}_commitIterable(t){Array.isArray(this.value)||(this.value=[],this.clear());const e=this.value;let n,i=0;for(const s of t)void 0===(n=e[i])&&(n=new d(this.options),e.push(n),0===i?n.appendIntoPart(this):n.insertAfterPart(e[i-1])),n.setValue(s),n.commit(),i++;i<e.length&&(e.length=i,this.clear(n&&n.endNode))}clear(t=this.startNode){Object(s.b)(this.startNode.parentNode,t.nextSibling,this.endNode)}}class p{constructor(t,e,n){if(this.value=void 0,this._pendingValue=void 0,2!==n.length||""!==n[0]||""!==n[1])throw new Error("Boolean attributes can only contain a single expression");this.element=t,this.name=e,this.strings=n}setValue(t){this._pendingValue=t}commit(){for(;Object(i.b)(this._pendingValue);){const t=this._pendingValue;this._pendingValue=r.a,t(this)}if(this._pendingValue===r.a)return;const t=!!this._pendingValue;this.value!==t&&(t?this.element.setAttribute(this.name,""):this.element.removeAttribute(this.name)),this.value=t,this._pendingValue=r.a}}class f extends u{constructor(t,e,n){super(t,e,n),this.single=2===n.length&&""===n[0]&&""===n[1]}_createPart(){return new m(this)}_getValue(){return this.single?this.parts[0].value:super._getValue()}commit(){this.dirty&&(this.dirty=!1,this.element[this.name]=this._getValue())}}class m extends h{}let _=!1;try{const t={get capture(){return _=!0,!1}};window.addEventListener("test",t,t),window.removeEventListener("test",t,t)}catch(t){}class g{constructor(t,e,n){this.value=void 0,this._pendingValue=void 0,this.element=t,this.eventName=e,this.eventContext=n,this._boundHandleEvent=(t=>this.handleEvent(t))}setValue(t){this._pendingValue=t}commit(){for(;Object(i.b)(this._pendingValue);){const t=this._pendingValue;this._pendingValue=r.a,t(this)}if(this._pendingValue===r.a)return;const t=this._pendingValue,e=this.value,n=null==t||null!=e&&(t.capture!==e.capture||t.once!==e.once||t.passive!==e.passive),s=null!=t&&(null==e||n);n&&this.element.removeEventListener(this.eventName,this._boundHandleEvent,this._options),s&&(this._options=v(t),this.element.addEventListener(this.eventName,this._boundHandleEvent,this._options)),this.value=t,this._pendingValue=r.a}handleEvent(t){"function"==typeof this.value?this.value.call(this.eventContext||this.element,t):this.value.handleEvent(t)}}const v=t=>t&&(_?{capture:t.capture,passive:t.passive,once:t.once}:t.capture)},function(t,e,n){"use strict";n.d(e,"a",function(){return i}),n.d(e,"b",function(){return s});const i={},s={}},function(t,e,n){"use strict";n.d(e,"a",function(){return i}),n.d(e,"c",function(){return s}),n.d(e,"b",function(){return r});const i=void 0!==window.customElements&&void 0!==window.customElements.polyfillWrapFlushCallback,s=(t,e,n=null,i=null)=>{let s=e;for(;s!==n;){const e=s.nextSibling;t.insertBefore(s,i),s=e}},r=(t,e,n=null)=>{let i=e;for(;i!==n;){const e=i.nextSibling;t.removeChild(i),i=e}}},,function(t,e,n){"use strict";function i(t,e=1e4){"object"==typeof t&&(t=t.message||JSON.stringify(t));var n={message:t,duration:e};document.dispatchEvent(new CustomEvent("error-sk",{detail:n,bubbles:!0}))}n.d(e,"a",function(){return i})},function(t,e,n){"use strict";function i(t){if(t.ok)return t.json();throw{message:`Bad network response: ${t.statusText}`,resp:t,status:t.status}}n.d(e,"a",function(){return i})},function(t,e,n){"use strict";n.d(e,"a",function(){return s}),n.d(e,"b",function(){return r});const i=new WeakMap,s=t=>(...e)=>{const n=t(...e);return i.set(n,!0),n},r=t=>"function"==typeof t&&i.has(t)},,function(t,e,n){"use strict";n.d(e,"b",function(){return r}),n.d(e,"a",function(){return o});var i=n(5),s=n(1);class r{constructor(t,e,n,i){this.strings=t,this.values=e,this.type=n,this.processor=i}getHTML(){const t=this.strings.length-1;let e="";for(let n=0;n<t;n++){const t=this.strings[n],i=s.e.exec(t);e+=i?t.substr(0,i.index)+i[1]+i[2]+s.b+i[3]+s.f:t+s.g}return e+this.strings[t]}getTemplateElement(){const t=document.createElement("template");return t.innerHTML=this.getHTML(),t}}class o extends r{getHTML(){return`<svg>${super.getHTML()}</svg>`}getTemplateElement(){const t=super.getTemplateElement(),e=t.content,n=e.firstChild;return e.removeChild(n),Object(i.c)(e,n.firstChild),t}}},,,function(t,e,n){"use strict";n.d(e,"a",function(){return r});var i=n(5),s=n(1);class r{constructor(t,e,n){this._parts=[],this.template=t,this.processor=e,this.options=n}update(t){let e=0;for(const n of this._parts)void 0!==n&&n.setValue(t[e]),e++;for(const t of this._parts)void 0!==t&&t.commit()}_clone(){const t=i.a?this.template.element.content.cloneNode(!0):document.importNode(this.template.element.content,!0),e=this.template.parts;let n=0,r=0;const o=t=>{const i=document.createTreeWalker(t,133,null,!1);let a=i.nextNode();for(;n<e.length&&null!==a;){const t=e[n];if(Object(s.d)(t))if(r===t.index){if("node"===t.type){const t=this.processor.handleTextExpression(this.options);t.insertAfterNode(a.previousSibling),this._parts.push(t)}else this._parts.push(...this.processor.handleAttributeExpressions(a,t.name,t.strings,this.options));n++}else r++,"TEMPLATE"===a.nodeName&&o(a.content),a=i.nextNode();else this._parts.push(void 0),n++}};return o(t),i.a&&(document.adoptNode(t),customElements.upgrade(t)),t}}},function(t,e,n){"use strict";n.d(e,"a",function(){return s});var i=n(0);const s=Object(i.b)(t=>e=>{if(void 0===t&&e instanceof i.a){if(t!==e.value){const t=e.committer.name;e.committer.element.removeAttribute(t)}}else e.setValue(t)})},,,,function(t,e,n){"use strict";n.d(e,"a",function(){return o});var i=n(7),s=n(0),r=n(2);class o extends HTMLElement{constructor(t){super(),this._template=t,this._app=null,this._auth_header="",this._notAuthorized=!1}connectedCallback(){Object(r.a)(this,"client_id"),Object(r.a)(this,"testing_offline"),this._authHeaderEvent=(t=>{this._auth_header=t.detail.auth_header}),this.addEventListener("log-in",this._authHeaderEvent)}disconnectedCallback(){this.removeEventListener("log-in",this._authHeaderEvent)}static get observedAttributes(){return["client_id","testing_offline"]}get app(){return this._app}get auth_header(){return this._auth_header}get loggedInAndAuthorized(){return!!this._auth_header&&!this._notAuthorized}get permissions(){return this._app&&this._app.permissions||{}}get server_details(){return this._app&&this._app.server_details||{}}get client_id(){return this.getAttribute("client_id")}set client_id(t){return this.setAttribute("client_id",t)}get testing_offline(){return this.hasAttribute("testing_offline")}set testing_offline(t){t?this.setAttribute("testing_offline",!0):this.removeAttribute("testing_offline")}fetchError(t,e){403===t.status?(this._message="User unauthorized - try logging in with a different account",this._notAuthorized=!0,this.render()):"AbortError"!==t.name&&(console.error(t),Object(i.a)(`Unexpected error loading ${e}: ${t.message}`,5e3)),this._app.finishedTask()}render(){Object(s.d)(this._template(this),this,{eventContext:this}),this._app||(this._app=this.firstElementChild,Object(s.d)(this._template(this),this,{eventContext:this}))}attributeChangedCallback(t,e,n){this.render()}}},function(t,e,n){"use strict";var i=n(7),s=n(0),r=n(15),o=n(8),a=n(2);window.customElements.define("toast-sk",class extends HTMLElement{constructor(){super(),this._timer=null}connectedCallback(){this.hasAttribute("duration")||(this.duration=5e3),Object(a.a)(this,"duration")}get duration(){return+this.getAttribute("duration")}set duration(t){this.setAttribute("duration",t)}show(){this.setAttribute("shown",""),this.duration>0&&!this._timer&&(this._timer=window.setTimeout(()=>{this._timer=null,this.hide()},this.duration))}hide(){this.removeAttribute("shown"),this._timer&&(window.clearTimeout(this._timer),this._timer=null)}});n(56);window.customElements.define("error-toast-sk",class extends HTMLElement{connectedCallback(){this.innerHTML="<toast-sk></toast-sk>",this._toast=this.firstElementChild,document.addEventListener("error-sk",this)}disconnectedCallback(){document.removeEventListener("error-sk",this)}handleEvent(t){t.detail.duration&&(this._toast.duration=t.detail.duration),this._toast.textContent=t.detail.message,this._toast.show()}});n(54);const c=document.createElement("template");c.innerHTML='<svg class="icon-sk-svg" xmlns="http://www.w3.org/2000/svg" width=24 height=24 viewBox="0 0 24 24"><path d="M20 8h-2.81c-.45-.78-1.07-1.45-1.82-1.96L17 4.41 15.59 3l-2.17 2.17C12.96 5.06 12.49 5 12 5c-.49 0-.96.06-1.41.17L8.41 3 7 4.41l1.62 1.63C7.88 6.55 7.26 7.22 6.81 8H4v2h2.09c-.05.33-.09.66-.09 1v1H4v2h2v1c0 .34.04.67.09 1H4v2h2.81c1.04 1.79 2.97 3 5.19 3s4.15-1.21 5.19-3H20v-2h-2.09c.05-.33.09-.66.09-1v-1h2v-2h-2v-1c0-.34-.04-.67-.09-1H20V8zm-6 8h-4v-2h4v2zm0-4h-4v-2h4v2z"/></svg>',window.customElements.define("bug-report-icon-sk",class extends HTMLElement{connectedCallback(){let t=c.content.cloneNode(!0);this.appendChild(t)}});const l=document.createElement("template");l.innerHTML='<svg class="icon-sk-svg" xmlns="http://www.w3.org/2000/svg" width=24 height=24 viewBox="0 0 24 24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>',window.customElements.define("menu-icon-sk",class extends HTMLElement{connectedCallback(){let t=l.content.cloneNode(!0);this.appendChild(t)}}),window.customElements.define("spinner-sk",class extends HTMLElement{connectedCallback(){Object(a.a)(this,"active")}get active(){return this.hasAttribute("active")}set active(t){t?this.setAttribute("active",""):this.removeAttribute("active")}});n(53),n(52);const u=new Promise((t,e)=>{const n=()=>{void 0!==window.gapi?t():setTimeout(n,10)};setTimeout(n,10)});window.customElements.define("oauth-login",class extends HTMLElement{connectedCallback(){Object(a.a)(this,"client_id"),Object(a.a)(this,"testing_offline"),this._auth_header="",this.testing_offline?this._profile={email:"missing@chromium.org",imageURL:"http://storage.googleapis.com/gd-wagtail-prod-assets/original_images/logo_google_fonts_color_2x_web_64dp.png"}:(this._profile=null,u.then(()=>{gapi.load("auth2",()=>{gapi.auth2.init({client_id:this.client_id}).then(()=>{this._maybeFireLoginEvent(),this.render()},t=>{console.error(t),Object(i.a)(`Error initializing oauth: ${JSON.stringify(t)}`,1e4)})})})),this.render()}static get observedAttributes(){return["client_id","testing_offline"]}get auth_header(){return this._auth_header}get client_id(){return this.getAttribute("client_id")}set client_id(t){return this.setAttribute("client_id",t)}get testing_offline(){return this.hasAttribute("testing_offline")}set testing_offline(t){t?this.setAttribute("testing_offline",!0):this.removeAttribute("testing_offline")}_maybeFireLoginEvent(){const t=gapi.auth2.getAuthInstance().currentUser.get();if(t.isSignedIn()){const e=t.getBasicProfile();this._profile={email:e.getEmail(),imageURL:e.getImageUrl()};const n=t.getAuthResponse(!0),i=`${n.token_type} ${n.access_token}`;return this.dispatchEvent(new CustomEvent("log-in",{detail:{auth_header:i},bubbles:!0})),this._auth_header=i,!0}return this._profile=null,this._auth_header="",!1}_logIn(){if(this.testing_offline)this._auth_header="Bearer 12345678910-boomshakalaka",this.dispatchEvent(new CustomEvent("log-in",{detail:{auth_header:this._auth_header},bubbles:!0})),this.render();else{const t=gapi.auth2.getAuthInstance();t&&t.signIn({scope:"email",prompt:"select_account"}).then(()=>{this._maybeFireLoginEvent()||console.warn("login was not successful; maybe user canceled"),this.render()})}}_logOut(){if(this.testing_offline)this._auth_header="",this.render(),window.location.reload();else{const t=gapi.auth2.getAuthInstance();t&&t.signOut().then(()=>{this._auth_header="",this._profile=null,window.location.reload()})}}render(){Object(s.d)((t=>t.auth_header?s["c"]` <div> <img class=center id=avatar src="${t._profile.imageURL}" width=30 height=30> <span class=center>${t._profile.email}</span> <span class=center>|</span> <a class=center @click=${t._logOut} href="#">Sign out</a> </div>`:s["c"]` <div> <a @click=${t._logIn} href="#">Sign in</a> </div>`)(this),this,{eventContext:this})}attributeChangedCallback(t,e,n){this.render()}});const h=document.createElement("template");h.innerHTML="\n<button class=toggle-button>\n  <menu-icon-sk>\n  </menu-icon-sk>\n</button>\n";const d=document.createElement("template");d.innerHTML="\n<div class=spinner-spacer>\n  <spinner-sk></spinner-sk>\n</div>\n";const p=document.createElement("template");p.innerHTML='\n<a target=_blank rel=noopener\n   href="https://bugs.chromium.org/p/chromium/issues/entry?components=Infra%3EPlatform%3ESwarming%3EWebUI&owner=kjlubick@chromium.org&status=Assigned">\n  <bug-report-icon-sk class=fab></bug-report-icon-sk>\n</a>',window.customElements.define("swarming-app",class extends HTMLElement{constructor(){super(),this._busyTaskCount=0,this._spinner=null,this._dynamicEle=null,this._auth_header="",this._server_details={server_version:"You must log in to see more details",bot_version:""},this._permissions={}}connectedCallback(){Object(a.a)(this,"client_id"),Object(a.a)(this,"testing_offline"),this._addHTML(),this.addEventListener("log-in",t=>{this._auth_header=t.detail.auth_header,this._fetch()}),this.render()}static get observedAttributes(){return["client_id","testing_offline"]}get busy(){return!!this._busyTaskCount}get permissions(){return this._permissions}get server_details(){return this._server_details}get client_id(){return this.getAttribute("client_id")}set client_id(t){return this.setAttribute("client_id",t)}get testing_offline(){return this.hasAttribute("testing_offline")}set testing_offline(t){t?this.setAttribute("testing_offline",!0):this.removeAttribute("testing_offline")}addBusyTasks(t){this._busyTaskCount+=t,this._spinner&&this._busyTaskCount>0&&(this._spinner.active=!0)}finishedTask(){this._busyTaskCount--,this._busyTaskCount<=0&&(this._busyTaskCount=0,this._spinner&&(this._spinner.active=!1),this.dispatchEvent(new CustomEvent("busy-end",{bubbles:!0})))}_addHTML(){const t=this.querySelector("header"),e=t&&t.querySelector("aside"),n=this.querySelector("footer");if(!(t&&e&&e.classList.contains("hideable")))return;let i=h.content.cloneNode(!0);t.insertBefore(i,t.firstElementChild),(i=t.firstElementChild).addEventListener("click",t=>this._toggleMenu(t,e));const s=d.content.cloneNode(!0);t.insertBefore(s,e),this._spinner=t.querySelector("spinner-sk");const r=document.createElement("span");r.classList.add("grow"),t.appendChild(r),this._dynamicEle=document.createElement("div"),this._dynamicEle.classList.add("right"),t.appendChild(this._dynamicEle);const o=document.createElement("error-toast-sk");n.append(o);const a=p.content.cloneNode(!0);n.append(a)}_toggleMenu(t,e){e.classList.toggle("shown")}_fetch(){if(!this._auth_header)return;this._server_details={server_version:"<loading>",bot_version:"<loading>"};const t={headers:{authorization:this._auth_header}};this.addBusyTasks(2),fetch("/_ah/api/swarming/v1/server/details",t).then(o.a).then(t=>{this._server_details=t,this.render(),this.dispatchEvent(new CustomEvent("server-details-loaded",{bubbles:!0})),this.finishedTask()}).catch(t=>{403===t.status?(this._server_details={server_version:"User unauthorized - try logging in with a different account",bot_version:""},this.render()):(console.error(t),Object(i.a)(`Unexpected error loading details: ${t.message}`,5e3)),this.finishedTask()}),fetch("/_ah/api/swarming/v1/server/permissions",t).then(o.a).then(t=>{this._permissions=t,this.render(),this.dispatchEvent(new CustomEvent("permissions-loaded",{bubbles:!0})),this.finishedTask()}).catch(t=>{403!==t.status&&(console.error(t),Object(i.a)(`Unexpected error loading permissions: ${t.message}`,5e3)),this.finishedTask()})}render(){this._dynamicEle&&Object(s.d)((t=>s["c"]` <div class=server-version> Server: <a href=${Object(r.a)(function(t){if(t&&t.server_version){var e=t.server_version.split("-");if(2===e.length)return`https://chromium.googlesource.com/infra/luci/luci-py/+/${e[1]}`}}(t._server_details))}> ${t._server_details.server_version} </a> </div> <oauth-login client_id=${t.client_id} ?testing_offline=${t.testing_offline}> </oauth-login>`)(this),this._dynamicEle)}attributeChangedCallback(t,e,n){this.render()}});n(51)},,,,,,,,,,,,,,function(t,e,n){"use strict";n.r(e);var i=n(0),s=(n(2),n(8)),r=(n(7),n(19));n(20);const o=t=>i["c"]` <swarming-app id=swapp client_id="${t.client_id}" ?testing_offline="${t.testing_offline}"> <header> <div class=title>Swarming</div> <aside class=hideable> <a href=/>Home</a> <a href=/botlist>Bot List</a> <a href=/tasklist>Task List</a> <a href=/bot>Bot Page</a> <a href=/task>Task Page</a> </aside> </header> <main> <h2>Service Status</h2> <div>Server Version: <span class=server_version> ${t.server_details.server_version}</span> </div> <div>Bot Version: ${t.server_details.bot_version} </div> <ul> <li>  <a href=/stats>Usage statistics</a> </li> <li> <a href=/restricted/mapreduce/status>Map Reduce Jobs</a> </li> <li> <a href=${(t=>"https://console.cloud.google.com/appengine/instances"+`project=${t._project_id}&versionId=${t.server_details.server_version}`)(t)}>View version's instances on Cloud Console</a> </li> <li> <a><a href=${(t=>`https://console.cloud.google.com/errors?project=${t}`)(t._project_id)}>View server errors on Cloud Console</a></a> </li> <li> <a><a href=${(t=>`https://console.cloud.google.com/logs/viewer?filters=status:500..599&project=${t}`)(t._project_id)}>View logs for HTTP 5xx on Cloud Console</a></a> </li> </ul> <h2>Configuration</h2> <ul>  <li> <a href="/restricted/config">View server config</a> </li> <li> <a href="/restricted/upload/bootstrap">View/upload bootstrap.py</a> </li> <li> <a href="/restricted/upload/bot_config">View/upload bot_config.py</a> </li> <li> <a href="/auth/groups">View/edit user groups</a> </li> </ul> ${t.permissions.get_bootstrap_token?(t=>i["c"]` <div> <h2>Bootstrapping a bot</h2> To bootstrap a bot, run one of these (all links are valid for 1 hour): <ol> <li> <strong> TL;DR; </strong> <pre class=command>python -c "import urllib; exec urllib.urlopen('${t._host_url}/bootstrap?tok=${t._bootstrap_token}').read()"</pre> </li> <li> Escaped version to pass as a ssh argument: <pre class=command>'python -c "import urllib; exec urllib.urlopen('"'${t._host_url}/bootstrap?tok=${t._bootstrap_token}'"').read()"'</pre> </li> <li> Manually: <pre class=command>mkdir bot; cd bot
rm -f swarming_bot.zip; curl -sSLOJ ${t._host_url}/bot_code?tok=${t._bootstrap_token}
python swarming_bot.zip</pre> </li> </ol> </div> `)(t):""} </main> <footer></footer> </swarming-app>`;window.customElements.define("swarming-index",class extends r.a{constructor(){super(o),this._bootstrap_token="...";const t=location.hostname.indexOf(".appspot.com");this._project_id=location.hostname.substring(0,t)||"not_found",this._host_url=location.origin}connectedCallback(){super.connectedCallback(),this.addEventListener("permissions-loaded",t=>{this.permissions.get_bootstrap_token&&this._fetchToken(),this.render()}),this.addEventListener("server-details-loaded",t=>{this.render()}),this.render()}_fetchToken(){const t={headers:{authorization:this.auth_header},method:"POST"};this.app.addBusyTasks(1),fetch("/_ah/api/swarming/v1/server/token",t).then(s.a).then(t=>{this._bootstrap_token=t.bootstrap_token,this.render(),this.app.finishedTask()}).catch(t=>this.fetchError(t,"token"))}});n(43)},,,,,,,,,function(t,e){},,,,,,,,function(t,e){},function(t,e){},function(t,e){},function(t,e){},,function(t,e){}]);