var wrapperElement = document.getElementById('wrapper');
var transitionTypeElement = document.getElementById('transition-type');
var transitionInProgress = false;

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
  loadByHash(hashUrl);
  wrapperElement.classList.remove('loading');
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
    updateSocketWithHash(hash);
  });
};

var kegStatus = document.getElementById('keg-status');
var updateKegStatus = function(kegerator) {
  console.log(kegerator);
  general.removeChildren(kegStatus);
  var p = general.createElementWithProp('p', {});
  p.textContent = kegerator.name + ' ';
  var i = general.createElementWithProp('i', {});
  i.textContent = kegerator.address + ':' + kegerator.port;
  p.appendChild(i);
  kegStatus.appendChild(p);
};

var socketConnection = null;
var keg_id = "56df340403ec679609351f2e";

var updateSocketWithHash = function(hash) {
  var prom = Promise.resolve();
  if(socketConnection === null) {
    // set up socket connection
    prom = new Promise(function(resolve, reject) {
      socketConnection = new WebSocket("ws://" + window.location.hostname + ":" + window.location.port + "/sockets");
      socketConnection.onopen = function(evt) {
        socketConnection.send(JSON.stringify({
          action: 'activate_keg',
          data: {
            id: keg_id
          }
        }));
      };
      socketConnection.onmessage = function(evt) {
        var parsed;
        console.log(evt.data);
        try {
          parsed = JSON.parse(evt.data);
          console.log(parsed);

          if(parsed.activeKeg) {
            updateKegStatus(parsed.activeKeg);
          }
        } catch (e) {
          // pass
        }
      };
    });

    //var interval = setInterval(function() {
    //  console.log('requesting temperatures...');
    //  socketConnection.send(JSON.stringify({
    //    action: "temps"
    //  }));
    //}, 20000);
  }
  return prom.then(function() {
    socketConnection.send(JSON.stringify({
      currentHash: hash
    }));
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
