!function(e){var t={};function n(i){if(t[i])return t[i].exports;var s=t[i]={i:i,l:!1,exports:{}};return e[i].call(s.exports,s,s.exports,n),s.l=!0,s.exports}n.m=e,n.c=t,n.d=function(e,t,i){n.o(e,t)||Object.defineProperty(e,t,{enumerable:!0,get:i})},n.r=function(e){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},n.t=function(e,t){if(1&t&&(e=n(e)),8&t)return e;if(4&t&&"object"==typeof e&&e&&e.__esModule)return e;var i=Object.create(null);if(n.r(i),Object.defineProperty(i,"default",{enumerable:!0,value:e}),2&t&&"string"!=typeof e)for(var s in e)n.d(i,s,function(t){return e[t]}.bind(null,s));return i},n.n=function(e){var t=e&&e.__esModule?function(){return e.default}:function(){return e};return n.d(t,"a",t),t},n.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},n.p="/newres/",n(n.s=9)}([function(e,t,n){"use strict";function i(e,t){if(e.hasOwnProperty(t)){let n=e[t];delete e[t],e[t]=n}}n.d(t,"a",function(){return i})},function(e,t,n){"use strict";const i=new WeakMap,s=e=>(i.set(e,!0),e),r=e=>"function"==typeof e&&i.has(e),o=void 0!==window.customElements&&void 0!==window.customElements.polyfillWrapFlushCallback,a=(e,t,n=null,i=null)=>{let s=t;for(;s!==n;){const t=s.nextSibling;e.insertBefore(s,i),s=t}},l=(e,t,n=null)=>{let i=t;for(;i!==n;){const t=i.nextSibling;e.removeChild(i),i=t}},u={},h=`{{lit-${String(Math.random()).slice(2)}}}`,c=`\x3c!--${h}--\x3e`,d=new RegExp(`${h}|${c}`),p=(()=>{const e=document.createElement("div");return e.setAttribute("style","{{bad value}}"),"{{bad value}}"!==e.getAttribute("style")})();class m{constructor(e,t){this.parts=[],this.element=t;let n=-1,i=0;const s=[],r=t=>{const o=t.content,a=document.createTreeWalker(o,133,null,!1);let l,u;for(;a.nextNode();){n++,l=u;const t=u=a.currentNode;if(1===t.nodeType){if(t.hasAttributes()){const s=t.attributes;let r=0;for(let e=0;e<s.length;e++)s[e].value.indexOf(h)>=0&&r++;for(;r-- >0;){const s=e.strings[i],r=g.exec(s)[2],o=p&&"style"===r?"style$":/^[a-zA-Z-]*$/.test(r)?r:r.toLowerCase(),a=t.getAttribute(o).split(d);this.parts.push({type:"attribute",index:n,name:r,strings:a}),t.removeAttribute(o),i+=a.length-1}}"TEMPLATE"===t.tagName&&r(t)}else if(3===t.nodeType){const e=t.nodeValue;if(e.indexOf(h)<0)continue;const r=t.parentNode,o=e.split(d),a=o.length-1;i+=a;for(let e=0;e<a;e++)r.insertBefore(""===o[e]?_():document.createTextNode(o[e]),t),this.parts.push({type:"node",index:n++});r.insertBefore(""===o[a]?_():document.createTextNode(o[a]),t),s.push(t)}else if(8===t.nodeType)if(t.nodeValue===h){const e=t.parentNode,r=t.previousSibling;null===r||r!==l||r.nodeType!==Node.TEXT_NODE?e.insertBefore(_(),t):n--,this.parts.push({type:"node",index:n++}),s.push(t),null===t.nextSibling?e.insertBefore(_(),t):n--,u=l,i++}else{let e=-1;for(;-1!==(e=t.nodeValue.indexOf(h,e+1));)this.parts.push({type:"node",index:-1})}}};r(t);for(const e of s)e.parentNode.removeChild(e)}}const f=e=>-1!==e.index,_=()=>document.createComment(""),g=/([ \x09\x0a\x0c\x0d])([^\0-\x1F\x7F-\x9F \x09\x0a\x0c\x0d"'>=/]+)([ \x09\x0a\x0c\x0d]*=[ \x09\x0a\x0c\x0d]*(?:[^ \x09\x0a\x0c\x0d"'`<>=]*|"[^"]*|'[^']*))$/;class v{constructor(e,t,n){this._parts=[],this.template=e,this.processor=t,this._getTemplate=n}update(e){let t=0;for(const n of this._parts)void 0!==n&&n.setValue(e[t]),t++;for(const e of this._parts)void 0!==e&&e.commit()}_clone(){const e=o?this.template.element.content.cloneNode(!0):document.importNode(this.template.element.content,!0),t=this.template.parts;let n=0,i=0;const s=e=>{const r=document.createTreeWalker(e,133,null,!1);let o=r.nextNode();for(;n<t.length&&null!==o;){const e=t[n];if(f(e))if(i===e.index){if("node"===e.type){const e=this.processor.handleTextExpression(this._getTemplate);e.insertAfterNode(o),this._parts.push(e)}else this._parts.push(...this.processor.handleAttributeExpressions(o,e.name,e.strings));n++}else i++,"TEMPLATE"===o.nodeName&&s(o.content),o=r.nextNode();else this._parts.push(void 0),n++}};return s(e),o&&(document.adoptNode(e),customElements.upgrade(e)),e}}class b{constructor(e,t,n,i){this.strings=e,this.values=t,this.type=n,this.processor=i}getHTML(){const e=this.strings.length-1;let t="",n=!0;for(let i=0;i<e;i++){const e=this.strings[i];t+=e;const s=e.lastIndexOf(">");!(n=(s>-1||n)&&-1===e.indexOf("<",s+1))&&p&&(t=t.replace(g,(e,t,n,i)=>"style"===n?`${t}style$${i}`:e)),t+=n?c:h}return t+this.strings[e]}getTemplateElement(){const e=document.createElement("template");return e.innerHTML=this.getHTML(),e}}class y extends b{getHTML(){return`<svg>${super.getHTML()}</svg>`}getTemplateElement(){const e=super.getTemplateElement(),t=e.content,n=t.firstChild;return t.removeChild(n),a(t,n.firstChild),e}}const x=e=>null===e||!("object"==typeof e||"function"==typeof e);class E{constructor(e,t,n){this.dirty=!0,this.element=e,this.name=t,this.strings=n,this.parts=[];for(let e=0;e<n.length-1;e++)this.parts[e]=this._createPart()}_createPart(){return new w(this)}_getValue(){const e=this.strings,t=e.length-1;let n="";for(let i=0;i<t;i++){n+=e[i];const t=this.parts[i];if(void 0!==t){const e=t.value;if(null!=e&&(Array.isArray(e)||"string"!=typeof e&&e[Symbol.iterator]))for(const t of e)n+="string"==typeof t?t:String(t);else n+="string"==typeof e?e:String(e)}}return n+e[t]}commit(){this.dirty&&(this.dirty=!1,this.element.setAttribute(this.name,this._getValue()))}}class w{constructor(e){this.value=void 0,this.committer=e}setValue(e){e===u||x(e)&&e===this.value||(this.value=e,r(e)||(this.committer.dirty=!0))}commit(){for(;r(this.value);){const e=this.value;this.value=u,e(this)}this.value!==u&&this.committer.commit()}}class T{constructor(e){this.value=void 0,this._pendingValue=void 0,this.templateFactory=e}appendInto(e){this.startNode=e.appendChild(_()),this.endNode=e.appendChild(_())}insertAfterNode(e){this.startNode=e,this.endNode=e.nextSibling}appendIntoPart(e){e._insert(this.startNode=_()),e._insert(this.endNode=_())}insertAfterPart(e){e._insert(this.startNode=_()),this.endNode=e.endNode,e.endNode=this.startNode}setValue(e){this._pendingValue=e}commit(){for(;r(this._pendingValue);){const e=this._pendingValue;this._pendingValue=u,e(this)}const e=this._pendingValue;e!==u&&(x(e)?e!==this.value&&this._commitText(e):e instanceof b?this._commitTemplateResult(e):e instanceof Node?this._commitNode(e):Array.isArray(e)||e[Symbol.iterator]?this._commitIterable(e):void 0!==e.then?this._commitPromise(e):this._commitText(e))}_insert(e){this.endNode.parentNode.insertBefore(e,this.endNode)}_commitNode(e){this.value!==e&&(this.clear(),this._insert(e),this.value=e)}_commitText(e){const t=this.startNode.nextSibling;e=null==e?"":e,t===this.endNode.previousSibling&&t.nodeType===Node.TEXT_NODE?t.textContent=e:this._commitNode(document.createTextNode("string"==typeof e?e:String(e))),this.value=e}_commitTemplateResult(e){const t=this.templateFactory(e);if(this.value&&this.value.template===t)this.value.update(e.values);else{const n=new v(t,e.processor,this.templateFactory),i=n._clone();n.update(e.values),this._commitNode(i),this.value=n}}_commitIterable(e){Array.isArray(this.value)||(this.value=[],this.clear());const t=this.value;let n,i=0;for(const s of e)void 0===(n=t[i])&&(n=new T(this.templateFactory),t.push(n),0===i?n.appendIntoPart(this):n.insertAfterPart(t[i-1])),n.setValue(s),n.commit(),i++;i<t.length&&(t.length=i,this.clear(n&&n.endNode))}_commitPromise(e){this.value=e,e.then(t=>{this.value===e&&(this.setValue(t),this.commit())})}clear(e=this.startNode){l(this.startNode.parentNode,e.nextSibling,this.endNode)}}class N{constructor(e,t,n){if(this.value=void 0,this._pendingValue=void 0,2!==n.length||""!==n[0]||""!==n[1])throw new Error("Boolean attributes can only contain a single expression");this.element=e,this.name=t,this.strings=n}setValue(e){this._pendingValue=e}commit(){for(;r(this._pendingValue);){const e=this._pendingValue;this._pendingValue=u,e(this)}if(this._pendingValue===u)return;const e=!!this._pendingValue;this.value!==e&&(e?this.element.setAttribute(this.name,""):this.element.removeAttribute(this.name)),this.value=e,this._pendingValue=u}}class k extends E{constructor(e,t,n){super(e,t,n),this.single=2===n.length&&""===n[0]&&""===n[1]}_createPart(){return new A(this)}_getValue(){return this.single?this.parts[0].value:super._getValue()}commit(){this.dirty&&(this.dirty=!1,this.element[this.name]=this._getValue())}}class A extends w{}class V{constructor(e,t){this.value=void 0,this._pendingValue=void 0,this.element=e,this.eventName=t}setValue(e){this._pendingValue=e}commit(){for(;r(this._pendingValue);){const e=this._pendingValue;this._pendingValue=u,e(this)}this._pendingValue!==u&&(null==this._pendingValue!=(null==this.value)&&(null==this._pendingValue?this.element.removeEventListener(this.eventName,this):this.element.addEventListener(this.eventName,this)),this.value=this._pendingValue,this._pendingValue=u)}handleEvent(e){"function"==typeof this.value?this.value.call(this.element,e):"function"==typeof this.value.handleEvent&&this.value.handleEvent(e)}}class C{handleAttributeExpressions(e,t,n){const i=t[0];return"."===i?new k(e,t.slice(1),n).parts:"@"===i?[new V(e,t.slice(1))]:"?"===i?[new N(e,t.slice(1),n)]:new E(e,t,n).parts}handleTextExpression(e){return new T(e)}}const L=new C;function O(e){let t=M.get(e.type);void 0===t&&(t=new Map,M.set(e.type,t));let n=t.get(e.strings);return void 0===n&&(n=new m(e,e.getTemplateElement()),t.set(e.strings,n)),n}const M=new Map,S=new WeakMap;function $(e,t,n=O){let i=S.get(t);void 0===i&&(l(t,t.firstChild),S.set(t,i=new T(n)),i.appendInto(t)),i.setValue(e),i.commit()}n.d(t,"a",function(){return j}),n.d(t,!1,function(){return b}),n.d(t,!1,function(){return y}),n.d(t,!1,function(){return h}),n.d(t,!1,function(){return c}),n.d(t,!1,function(){return d}),n.d(t,!1,function(){return p}),n.d(t,!1,function(){return m}),n.d(t,!1,function(){return f}),n.d(t,!1,function(){return _}),n.d(t,!1,function(){return g}),n.d(t,!1,function(){return C}),n.d(t,!1,function(){return L}),n.d(t,!1,function(){return v}),n.d(t,!1,function(){return u}),n.d(t,!1,function(){return x}),n.d(t,!1,function(){return E}),n.d(t,!1,function(){return w}),n.d(t,!1,function(){return T}),n.d(t,!1,function(){return N}),n.d(t,!1,function(){return k}),n.d(t,!1,function(){return A}),n.d(t,!1,function(){return V}),n.d(t,!1,function(){return o}),n.d(t,!1,function(){return a}),n.d(t,!1,function(){return l}),n.d(t,!1,function(){return s}),n.d(t,!1,function(){return r}),n.d(t,!1,function(){return S}),n.d(t,"b",function(){return $}),n.d(t,!1,function(){return O}),n.d(t,!1,function(){return M});const j=(e,...t)=>new b(e,t,"html",L)},function(e,t,n){"use strict";function i(e,t=1e4){"object"==typeof e&&(e=e.message||JSON.stringify(e));var n={message:e,duration:t};document.dispatchEvent(new CustomEvent("error-sk",{detail:n,bubbles:!0}))}n.d(t,"a",function(){return i})},function(e,t,n){"use strict";function i(e){if(e.ok)return e.json();throw{message:`Bad network response: ${e.statusText}`,resp:e,status:e.status}}n.d(t,"a",function(){return i})},function(e,t,n){"use strict";var i=n(1),s=n(0),r=n(3),o=n(2);n(16);const a=document.createElement("template");a.innerHTML='<svg class="icon-sk-svg" xmlns="http://www.w3.org/2000/svg" width=24 height=24 viewBox="0 0 24 24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>',window.customElements.define("menu-icon-sk",class extends HTMLElement{connectedCallback(){let e=a.content.cloneNode(!0);this.appendChild(e)}}),window.customElements.define("spinner-sk",class extends HTMLElement{connectedCallback(){Object(s.a)(this,"active")}get active(){return this.hasAttribute("active")}set active(e){e?this.setAttribute("active",""):this.removeAttribute("active")}});n(14),n(13);window.customElements.define("oauth-login",class extends HTMLElement{connectedCallback(){Object(s.a)(this,"client_id"),Object(s.a)(this,"testing_offline"),this._auth_header="",this.testing_offline?this._profile={email:"missing@chromium.org",imageURL:"http://storage.googleapis.com/gd-wagtail-prod-assets/original_images/logo_google_fonts_color_2x_web_64dp.png"}:(this._profile=null,document.addEventListener("oauth-lib-loaded",()=>{gapi.auth2.init({client_id:this.client_id}).then(()=>{this._maybeFireLoginEvent(),this._render()},e=>{console.error(e),Object(o.a)(`Error initializing oauth: ${JSON.stringify(e)}`,1e4)})})),this._render()}static get observedAttributes(){return["client_id","testing_offline"]}get auth_header(){return this._auth_header}get client_id(){return this.getAttribute("client_id")}set client_id(e){return this.setAttribute("client_id",e)}get testing_offline(){return this.hasAttribute("testing_offline")}set testing_offline(e){e?this.setAttribute("testing_offline",!0):this.removeAttribute("testing_offline")}_maybeFireLoginEvent(){let e=gapi.auth2.getAuthInstance().currentUser.get();if(e.isSignedIn()){let t=e.getBasicProfile();this._profile={email:t.getEmail(),imageURL:t.getImageUrl()};let n=e.getAuthResponse(!0),i=`${n.token_type} ${n.access_token}`;return this.dispatchEvent(new CustomEvent("log-in",{detail:{auth_header:i},bubbles:!0})),this._auth_header=i,!0}return this._profile=null,this._auth_header="",!1}_logIn(){if(this.testing_offline)this._auth_header="Bearer 12345678910-boomshakalaka",this.dispatchEvent(new CustomEvent("log-in",{detail:{auth_header:this._auth_header},bubbles:!0})),this._render();else{let e=gapi.auth2.getAuthInstance();e&&e.signIn({scope:"email",prompt:"select_account"}).then(()=>{this._maybeFireLoginEvent()||console.warn("login was not successful; maybe user canceled"),this._render()})}}_logOut(){if(this.testing_offline)this._auth_header="",this._render(),window.location.reload();else{let e=gapi.auth2.getAuthInstance();e&&e.signOut().then(()=>{this._auth_header="",this._profile=null,window.location.reload()})}}_render(){Object(i.b)((e=>e.auth_header?i["a"]` <div> <img class=center id=avatar src="${e._profile.imageURL}" width=30 height=30> <span class=center>${e._profile.email}</span> <span class=center>|</span> <a class=center @click=${()=>e._logOut()} href="#">Sign out</a> </div>`:i["a"]` <div> <a @click=${()=>e._logIn()} href="#">Sign in</a> </div>`)(this),this)}attributeChangedCallback(e,t,n){this._render()}});const l=document.createElement("template");l.innerHTML="\n<button class=toggle-button>\n  <menu-icon-sk>\n  </menu-icon-sk>\n</button>\n";const u=document.createElement("template");u.innerHTML="\n<div class=spinner-spacer>\n  <spinner-sk></spinner-sk>\n</div>\n";window.customElements.define("swarming-app",class extends HTMLElement{constructor(){super(),this._busyTaskCount=0,this._spinner=null,this._dynamicEle=null,this._auth_header="",this._server_details={server_version:"You must log in to see more details",bot_version:""},this._permissions={}}connectedCallback(){Object(s.a)(this,"client_id"),Object(s.a)(this,"testing_offline"),this._addHTML(),this.addEventListener("log-in",e=>{this._auth_header=e.detail.auth_header,this._fetch()}),this._render()}static get observedAttributes(){return["client_id","testing_offline"]}get busy(){return!!this._busyTaskCount}get permissions(){return this._permissions}get server_details(){return this._server_details}get client_id(){return this.getAttribute("client_id")}set client_id(e){return this.setAttribute("client_id",e)}get testing_offline(){return this.hasAttribute("testing_offline")}set testing_offline(e){e?this.setAttribute("testing_offline",!0):this.removeAttribute("testing_offline")}addBusyTasks(e){this._busyTaskCount+=e,this._spinner&&this._busyTaskCount>0&&(this._spinner.active=!0)}finishedTask(){this._busyTaskCount--,this._busyTaskCount<=0&&(this._busyTaskCount=0,this._spinner&&(this._spinner.active=!1),this.dispatchEvent(new CustomEvent("busy-end",{bubbles:!0})))}_addHTML(){let e=this.querySelector("header"),t=e&&e.querySelector("aside");if(!(e&&t&&t.classList.contains("hideable")))return;let n=l.content.cloneNode(!0);e.insertBefore(n,e.firstElementChild),(n=e.firstElementChild).addEventListener("click",e=>this._toggleMenu(e,t));let i=u.content.cloneNode(!0);e.insertBefore(i,t),this._spinner=e.querySelector("spinner-sk");let s=document.createElement("span");s.classList.add("grow"),e.appendChild(s),this._dynamicEle=document.createElement("div"),this._dynamicEle.classList.add("right"),e.appendChild(this._dynamicEle)}_toggleMenu(e,t){t.classList.toggle("shown")}_fetch(){if(!this._auth_header)return;this._server_details={server_version:"<loading>",bot_version:"<loading>"};let e={headers:{authorization:this._auth_header}};this.addBusyTasks(2),fetch("/_ah/api/swarming/v1/server/details",e).then(r.a).then(e=>{this._server_details=e,this._render(),this.dispatchEvent(new CustomEvent("server-details-loaded",{bubbles:!0})),this.finishedTask()}).catch(e=>{403===e.status?(this._server_details={server_version:"User unauthorized - try logging in with a different account",bot_version:""},this._render()):(console.error(e),Object(o.a)(`Unexpected error loading details: ${e.message}`,5e3)),this.finishedTask()}),fetch("/_ah/api/swarming/v1/server/permissions",e).then(r.a).then(e=>{this._permissions=e,this._render(),this.dispatchEvent(new CustomEvent("permissions-loaded",{bubbles:!0})),this.finishedTask()}).catch(e=>{403!==e.status&&(console.error(e),Object(o.a)(`Unexpected error loading permissions: ${e.message}`,5e3)),this.finishedTask()})}_render(){this._dynamicEle&&Object(i.b)((e=>i["a"]` <div class=server-version> Server: <a href=${function(e){if(!e||!e.server_version)return"#";var t=e.server_version.split("-");return 2!==t.length?"#":`https://chromium.googlesource.com/infra/luci/luci-py/+/${t[1]}`}(e._server_details)}> ${e._server_details.server_version} </a> </div> <oauth-login client_id=${e.client_id} ?testing_offline=${e.testing_offline}> </oauth-login> `)(this),this._dynamicEle)}attributeChangedCallback(e,t,n){this._render()}});n(12)},,,,,function(e,t,n){"use strict";n.r(t);n(4)},,,function(e,t){},function(e,t){},function(e,t){},,function(e,t){}]);