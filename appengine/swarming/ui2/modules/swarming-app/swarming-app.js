// Copyright 2018 The LUCI Authors. All rights reserved.
// Use of this source code is governed under the Apache License, Version 2.0
// that can be found in the LICENSE file.

/** @module swarming-ui/modules/swarming-app
 * @description <h2><code>swarming-app</code></h2>
 * <p>
 *   A general application layout which includes a responsive
 *   side panel. This element is largely CSS, with a smattering of
 *   JS to toggle the side panel on/off when in small screen mode.
 *   A notable addition to the top panel is an &lt;oauth-login&gt; element
 *   to handle login. See the demo page for an example usage.
 * </p>
 *
 * <p>
 *   The swarming-app can be a central place for indicating to the user
 *   that the app is busy (e.g. RPCs). Simply use the addBusyTasks()
 *   and finishedTask() to indicate when work is starting and stopping.
 *   The 'busy-end' event will signal any time a finishedTask() drops the
 *   count of ongoing tasks to zero (or lower). See also the busy property.
 * </p>
 *
 * @evt busy-end This event is emitted whenever the app transitions from
 *               busy to not busy.
 *
 * @attr testing_offline - If true, the real login flow won't be used.
 *    Instead, dummy data will be used. Ideal for local testing.
 *
 */

import 'elements-sk/error-toast-sk';
import 'elements-sk/icon/bug-report-icon-sk';
import 'elements-sk/icon/menu-icon-sk';
import 'elements-sk/spinner-sk';
import '../oauth-login';

import {jsonOrThrow} from 'common-sk/modules/jsonOrThrow';
import * as query from 'common-sk/modules/query';
import {errorMessage} from 'elements-sk/errorMessage';
import {upgradeProperty} from 'elements-sk/upgradeProperty';
import {html, render} from 'lit-html';
import {ifDefined} from 'lit-html/directives/if-defined';

const button_template = document.createElement('template');
button_template.innerHTML = `
<button class=toggle-button>
  <menu-icon-sk>
  </menu-icon-sk>
</button>
`;

const spinner_template = document.createElement('template');
spinner_template.innerHTML = `
<div class=spinner-spacer>
  <spinner-sk></spinner-sk>
</div>
`;

const pantheon_url = `https://console.cloud.google.com/appengine/versions?project=`;
const version_filter_prefix = `&serviceId=default&pageState=(%22versionsTable` +
  `%22:(%22f%22:%22%255B%257B_22k_22_3A_22Version` +
  `_22_2C_22t_22_3A10_2C_22v_22_3A_22_5C_22`;
const version_filter_postfix = `_5C_22_22_2C_22s_22_3Atrue_2C_22i_22_3A_22` +
  `id_22%257D%255D%22))`;
const version_default = 'You must log in to see more details';

function serverLink(project_id, details) {
  if (!details || !details.server_version) {
    return version_default;
  }
  return html`<a href=${pantheon_url.concat(project_id,
      version_filter_prefix, details.server_version, version_filter_postfix)}>
      ${details.server_version}</a>`;
}

function gitLink(details) {
  if (!details || !details.server_version) {
    return '';
  }

  const split = details.server_version.split('-');
  if (split.length >= 3) {
    console.error(`Invalid Git version. version=${details.server_version}`);
    return '';
  }
  const version = (split.length == 2) ? split[1] : split[0];
  return html`<a href=https://chromium.googlesource.com/infra/luci/luci-py/+/${version}>${version}</a>`;
}

const dynamic_content_template = (ele) => html`
<div class=server-version>
  AppEngine version: ${serverLink(ele._project_id, ele._server_details)} Git version:${gitLink(ele._server_details)}
</div>
<oauth-login ?testing_offline=${ele.testing_offline}>
</oauth-login>`;

const fab_template = document.createElement('template');
fab_template.innerHTML = `
<a target=_blank rel=noopener
   href="https://bugs.chromium.org/p/chromium/issues/entry?components=Infra%3ELUCI%3ETaskDistribution%3EUI&owner=kjlubick@chromium.org&status=Assigned">
  <bug-report-icon-sk class=fab></bug-report-icon-sk>
</a>`;

window.customElements.define('swarming-app', class extends HTMLElement {
  constructor() {
    super();
    this._busyTaskCount = 0;
    this._spinner = null;
    this._dynamicEle = null;
    this._auth_header = '';
    this._profile = {};
    this._server_details = {
      server_version: version_default,
      bot_version: '',
      cas_viewer_server: '',
    };
    const idx = location.hostname.indexOf('.appspot.com');
    this._project_id = location.hostname.substring(0, idx);
    this._permissions = {};
  }

  connectedCallback() {
    upgradeProperty(this, 'testing_offline');
    this._addHTML();

    this.addEventListener('log-in', (e) => {
      this._auth_header = e.detail.auth_header;
      this._profile = e.detail.profile;
      this._fetch();
    });

    this.render();
  }

  static get observedAttributes() {
    return ['testing_offline'];
  }


  /** @prop {boolean} busy Indicates if there any on-going tasks (e.g. RPCs).
   *                  This also mirrors the status of the embedded spinner-sk.
   *                  Read-only. */
  get busy() {
    return !!this._busyTaskCount;
  }

  /** @prop {Object} permissions The permissions the server says the logged-in
                     user has. This is empty object if user is not logged in.
   *                 Read-only. */
  get permissions() {
    return this._permissions;
  }

  /** @prop {Object} profile An object with keys email and imageURL of the
                             logged in user. Read Only. */
  get profile() {
    return this._profile;
  }

  /** @prop {Object} server_details The details about the server or a
                     placeholder object if the user is not logged in or
   *                 not authorized. Read-only. */
  get server_details() {
    return this._server_details;
  }

  /** @prop {bool} testing_offline Mirrors the attribute 'testing_offline'. */
  get testing_offline() {
    return this.hasAttribute('testing_offline');
  }
  set testing_offline(val) {
    if (val) {
      this.setAttribute('testing_offline', true);
    } else {
      this.removeAttribute('testing_offline');
    }
  }

  /**
   * Indicate there are some number of tasks (e.g. RPCs) the app is waiting on
   * and should be in the "busy" state, if it isn't already.
   *
   * @param {Number} count - Number of tasks to wait for. Should be positive.
   */
  addBusyTasks(count) {
    this._busyTaskCount += count;
    if (this._spinner && this._busyTaskCount > 0) {
      this._spinner.active = true;
    }
  }

  /**
   * Removes one task from the busy count. If there are no more tasks to wait
   * for, the app will leave the "busy" state and emit the "busy-end" event.
   *
   */
  finishedTask() {
    this._busyTaskCount--;
    if (this._busyTaskCount <= 0) {
      this._busyTaskCount = 0;
      if (this._spinner) {
        this._spinner.active = false;
      }
      this.dispatchEvent(new CustomEvent('busy-end', {bubbles: true}));
    }
  }

  /**
   * As mentioned in the element description, the main point of this element
   * is to insert a little bit of CSS and a few HTML elements for consistent
   * theming and functionality.
   *
   * This function adds in the following:
   * <ol>
   *   <li> A button that will toggle the side panel on small screens (and will
   *      be hidden on large screens).</li>
   *   <li> The spinner that indicates the busy state.</li>
   *   <li> A spacer span to right-align the following elements.</li>
   *   <li> A placeholder in which to render information about the server.</li>
   *   <li> A placeholder in which to render the login-element.</li>
   *   <li> An error-toast-sk element in the footer. </li>
   *   <li> A floating action button for feedback in the footer. </li>
   * </ol>
   *
   * This function need only be called once, when the element is created.
   */
  _addHTML() {
    const header = this.querySelector('header');
    const sidebar = header && header.querySelector('aside');
    const footer = this.querySelector('footer');
    if (!(header && sidebar && sidebar.classList.contains('hideable'))) {
      return;
    }
    // Add the collapse button to the header as the first item.
    let btn = button_template.content.cloneNode(true);
    // btn is a document-fragment, so we need to insert it into the
    // DOM to make it "expand" into a real button. Then, and only then,
    // we can add a "click" listener.
    header.insertBefore(btn, header.firstElementChild);
    btn = header.firstElementChild;
    btn.addEventListener('click', (e) => this._toggleMenu(e, sidebar));

    // Add the spinner that will visually indicate the state of the
    // busy property.
    const spinner = spinner_template.content.cloneNode(true);
    header.insertBefore(spinner, sidebar);
    // The real spinner is a child of the template, so we need to grab it
    // from the header after the template has been expanded.
    this._spinner = header.querySelector('spinner-sk');

    const spacer = document.createElement('span');
    spacer.classList.add('grow');
    header.appendChild(spacer);

    // The placeholder for which the server details and login element (the only
    // dynamic content swarming-app manages) will be rendered into. See
    // render() for when that happens.
    this._dynamicEle = document.createElement('div');
    this._dynamicEle.classList.add('right');
    header.appendChild(this._dynamicEle);

    // Add things to the footer
    const errorToast = document.createElement('error-toast-sk');
    footer.append(errorToast);

    const fab = fab_template.content.cloneNode(true);
    footer.append(fab);
  }

  _toggleMenu(e, sidebar) {
    sidebar.classList.toggle('shown');
  }

  _fetch() {
    if (!this._auth_header) {
      return;
    }
    this._server_details = {
      server_version: '<loading>',
      bot_version: '<loading>',
    };
    const auth = {
      headers: {'authorization': this._auth_header},
    };
    this.addBusyTasks(1);
    fetch('/_ah/api/swarming/v1/server/details', auth)
        .then(jsonOrThrow)
        .then((json) => {
          this._server_details = json;
          this.render();
          this.dispatchEvent(new CustomEvent('server-details-loaded',
              {bubbles: true}));
          this.finishedTask();
        })
        .catch((e) => {
          if (e.status === 403) {
            this._server_details = {
              server_version: 'User unauthorized - try logging in ' +
              'with a different account',
              bot_version: '',
            };
            this.render();
          } else {
            console.error(e);
            errorMessage(`Unexpected error loading details: ${e.message}`, 5000);
          }
          this.finishedTask();
        });
    this._fetchPermissions(auth);
  }

  _fetchPermissions(auth, params) {
    this.addBusyTasks(1);
    let url = '/_ah/api/swarming/v1/server/permissions';
    if (params) url += `?${query.fromObject(params)}`;
    return fetch(url, auth)
        .then(jsonOrThrow)
        .then((json) => {
          this._permissions = json;
          this.render();
          this.dispatchEvent(new CustomEvent('permissions-loaded',
              {bubbles: true}));
          this.finishedTask();
        })
        .catch((e) => {
          if (e.status !== 403) {
            console.error(e);
            errorMessage(`Unexpected error loading permissions: ${e.message}`,
                5000);
          }
          this.finishedTask();
        });
  }

  render() {
    if (this._dynamicEle) {
      render(dynamic_content_template(this), this._dynamicEle);
    }
  }

  attributeChangedCallback(attrName, oldVal, newVal) {
    this.render();
  }
});
