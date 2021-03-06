var wrapperElement = document.getElementById('wrapper');
var transitionTypeElement = document.getElementById('transition-type');
var defaultKegeratorElement = document.getElementById('default-kegerator');
var kegeratorStatusElement = document.getElementById('kegerator-status-indicator');
var transitionInProgress = false;
var socketConnection = null;
var keg_id = "56df340403ec679609351f2e";
var defaultKegerator = null;

var hashChangeListenerEvent = function(evt) {
  var hashUrl = window.location.hash.slice(1);
  loadByHash(hashUrl);
};

window.addEventListener('popstate', hashChangeListenerEvent);

// call function after disabling hash listener
var disableHashChangeAndDo = function(func) {
  window.removeEventListener('popstate', hashChangeListenerEvent);
  func();
  window.addEventListener('popstate', hashChangeListenerEvent);
};

var changeHashWithoutEvent = function(hash) {
  return disableHashChangeAndDo(function() {
    return window.location.replace('#' + hash.split('#').join(''));
  });
};

// when doc loads, load correct hash content
document.addEventListener('DOMContentLoaded', function() {
  var hashUrl = window.location.hash.slice(1);
  if(hashUrl === ""){
    changeHashWithoutEvent('#/index');
  }
  loadByHash(hashUrl).then(function() {
    defaultKegerator = defaultKegerator || localStorage.getItem('defaultKegerator');
    if(defaultKegerator) {
      defaultKegeratorElement.value = defaultKegerator;
    }
    if(socketConnection && defaultKegerator) {
      socketConnection.send(JSON.stringify({
        action: 'activate_keg',
        data: {
          id: defaultKegerator
        }
      }));
    }
  });
  wrapperElement.classList.remove('loading');
});

var updateKegeratorStatus = function(stat) {
  console.log(stat);
  if(stat === "ok") {
    kegeratorStatusElement.classList.remove('glyphicon-refresh');
    kegeratorStatusElement.classList.remove('glyphicon-remove');
    kegeratorStatusElement.classList.add('glyphicon-ok');
  } else {
    kegeratorStatusElement.classList.remove('glyphicon-refresh');
    kegeratorStatusElement.classList.remove('glyphicon-ok');
    kegeratorStatusElement.classList.add('glyphicon-remove');
  }
};

defaultKegeratorElement.addEventListener('change', function(evt) {
  defaultKegerator = defaultKegeratorElement.value;
  localStorage.setItem('defaultKegerator', defaultKegerator);
  if(socketConnection && socketConnection.readyState == 1) {
    socketConnection.send(JSON.stringify({
      action: 'activate_keg',
      data: {
        id: defaultKegerator
      }
    }));
  }
});

// load content at hash url
var loadByHash = function(raw_hashUrl) {
  // clean up trailing / leading '/'s
  var hashUrl = raw_hashUrl.split('/').filter(function(e){return e;}).join('/');
  if(hashUrl === "") {
    hashUrl = 'index';
  }
  // check that a view aleady exists
  var existingElement = wrapperElement.querySelector('[hash-url="' + hashUrl + '"]');
  var prom = Promise.resolve(hashUrl);
  if(!(existingElement && existingElement.hasAttribute('static'))) {
    // make request
    var fullUrl = '/hash/' + hashUrl;
    var html;
    var newHashUrl;
    prom = general.makeRequest(fullUrl, "GET", null, null).then(function(request) {
      console.log("success");
      var data = JSON.parse(request.responseText);

      newHashUrl = data.hash_id;
      html = data.html;

      return request;

    }).catch(function(request) {
      console.log("failure");
      newHashUrl = fullUrl.split('hash/').slice(1)[0];
      try {
        html = JSON.parse(request.response).html;
      } catch (e) {
      }
      if(!html) {
        if(request.status >= 400 && request.status < 500) {
          html = "<div>4XX Error</div>";
        } else {
          html = "<div>5XX Error</div>";
        }
      }
      return request;
    }).then(function(request) {
      if(newHashUrl !== hashUrl) {
        // redirected
        changeHashWithoutEvent(newHashUrl);
        existingElement = wrapperElement.querySelector('[hash-url="' + newHashUrl + '"]');
      }
      var outerDivProps = {
        'class':'outer',
        'hash-url': newHashUrl
      };
      var outerDiv = general.createElementWithProp('div', outerDivProps);
      var innerDiv = general.createElementWithProp('div', {'class': 'inner'});
      innerDiv.innerHTML = html;
      outerDiv.appendChild(innerDiv);

      if(existingElement) {
        // replace it
        wrapperElement.replaceChild(outerDiv, existingElement);
      } else {
        // append it
        wrapperElement.appendChild(outerDiv);
      }
      // set to active

      // activate scripts
      var scripts = innerDiv.getElementsByTagName('script');
      for(var i=0, elem; elem = scripts[i], i < scripts.length; i++) {
        eval(elem.innerHTML); // jshint ignore:line
      }

      return newHashUrl;
    });
  }
  return prom.then(function(hash) {
    setActiveTo(hash, true);
    return updateSocketWithHash(hash);
  });
};

var socketMessageEventListener = function(evt) {
  var message = evt.data;
  var parsedMessage = null;
  try {
    parsedMessage = JSON.parse(message);
  } catch(e) {}

  console.log(parsedMessage || message);
  if(parsedMessage && 'action' in parsedMessage) {
    switch (parsedMessage.action) {
      case "activate_keg":
        updateKegeratorStatus(parsedMessage.status);
        break;
      default:
        console.log("unknown action");
        return;
    }
  }
};

var setupSocketConnection = function(url) {
  return new Promise(function(resolve, reject) {
    var initError = function (err) {return reject(err);};
    var connection = new WebSocket(url);
    connection.onerror = initError;
    connection.onopen = function socketOpenEvent(evt) {
      connection.removeEventListener('error', initError);
      return resolve(connection);
    };
    connection.onmessage = socketMessageEventListener;
  }).then(function(conn) {
    conn.onerror = function(err) {
      alert("websocket server disconnected, refresh to repair");
    };
    return conn;
  });
};

var updateSocketWithHash = function(hash) {
  var socketSetupPromise = Promise.resolve();
  if(socketConnection === null) {
    var socketUrl = "ws://" + window.location.hostname + ":" + window.location.port + "/sockets";
    socketSetupPromise = setupSocketConnection(socketUrl).then(function(connection) {
      socketConnection = connection;
    });
  }
  return socketSetupPromise.then(function() {
    socketConnection.send(JSON.stringify({
      currentHash: hash
    }));
  }).catch(function(err) {
    // socket setup failed
    alert("failed to connect to websocket server");
    console.log(err);
  });
};

var transition = function(firstElement, secondElement, transformType) {
  transitionInProgress = true;
  var f, s;
  return new Promise(function(resolve, reject) {
    return setTimeout(function() {
      f = firstElement.firstChild.getBoundingClientRect();
      s = secondElement.firstChild.getBoundingClientRect();
      var transform, inverseTransform;
      switch (transformType) {
        case "scale":
          inverseTransform = "scale(" + f.width / s.width + ", " + f.height / s.height + ")";
          transform = "scale(" + s.width / f.width + ", " + s.height / f.height + ")";
          break;
        case "slide":
          transform = "translateX(" + (f.left + f.width) + "px)";
          inverseTransform = "translateX(" + (-s.left - s.width) + "px)";
          break;
        case "sliderev":
          transform = "translateX(" + (-f.left - f.width) + "px)";
          inverseTransform = "translateX(" + (s.left + s.width) + "px)";
          break;

      }
      secondElement.firstChild.style.transform = inverseTransform;
      return setTimeout(function() {
        secondElement.classList.remove('ready');
        secondElement.classList.add('transitioning');
        secondElement.classList.add('active');
      
        firstElement.classList.add('transitioning');
        firstElement.classList.remove('active');

        firstElement.firstChild.style.transform = transform;
        secondElement.firstChild.style.transform = "";

        return setTimeout(function() {
          firstElement.firstChild.style.transform = "";
          firstElement.classList.remove('transitioning');
          secondElement.classList.remove('transitioning');
          transitionInProgress = false;
          return resolve();
        }, 500);
      }, 50);
    }, 50);
  });
};

var getTransitionType = function(rev) {
  var value = transitionTypeElement.value;
  if(rev && value === "slide") {
    return "sliderev";
  }
  return value;
};

var setActiveTo = function(loc, animate) {
  var selector = '[hash-url="' + loc + '"]';
  var div = wrapperElement.querySelector('[hash-url="' + loc + '"]');
  var oldDiv = wrapperElement.querySelector('.active');
  if(div == oldDiv) {
    return;
  }
  if(!oldDiv) {
    div.classList.add('active');
  } else if(animate) {
    transition(oldDiv, div, getTransitionType(true));
  } else if (div !== oldDiv) {
    oldDiv.classList.remove('active');
    div.classList.add('active');
  }
};
