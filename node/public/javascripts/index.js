var createElementWithProp = function(elementName, properties) {
  var elem = document.createElement(elementName);
  for(var prop in properties) {
    elem.setAttribute(prop, properties[prop]);
  }
  return elem;
};

var makeRequest = function(url, method, data, updateFunc) {
  return new Promise(function(resolve, reject) {
    var request = new XMLHttpRequest();
    request.open(method, url, true);
    request.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    request.onload = function() {
      if (request.status >= 200 && request.status < 400) {
        return resolve(request);
      } else {
        return reject(request);
      }
    };
    request.onerror = function(error) {
      return reject(error);
    };
    if(updateFunc) {
      request.onprogress = updateFunc;
    }
    request.send(data);
  });
};

var disableButtons = function(state) {
  if(state) {
    nextButton.disabled = true;
    previousButton.disabled = true;
  } else {
    nextButton.disabled = false;
    previousButton.disabled = false;
  }
};

var wrapperElement = document.getElementById('wrapper');
var transition_type = document.getElementById('transition-type');

var transitionInProgress = false;
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
  var value = transition_type.value;
  if(rev && value === "slide") {
    return "sliderev";
  }
  return value;
};

var loadByHashId = function(hash_id) {
  var outer = wrapperElement.querySelector('[hash-url="' + hash_id + '"]');
  if(!outer || !(outer.hasAttribute('static') || outer.hasAttribute('fresh'))) {
    var url = '/hash/' + hash_id;
    makeRequest(url, 'GET', null, null).then(function(request) {
      var result = JSON.parse(request.response);
      var hashBasic = result.hash_id.split('?')[0].split('/')[0];

      var outerDivProps = {'class': 'outer', 'id':hashBasic};
      // uhh gayyy
      if(result.hash_id !== hash_id) {
        outerDivProps.fresh = "";
      }
      var outerDiv = createElementWithProp('div', outerDivProps);
      outerDiv.setAttribute('hash-url', hashBasic);
      var innerDiv = createElementWithProp('div', {'class': 'inner'});
      innerDiv.innerHTML = result.html;
      outerDiv.appendChild(innerDiv);

      var exisitingDiv = wrapperElement.querySelector('[hash-url="' + hashBasic + '"]');

      if(exisitingDiv) {
        wrapperElement.replaceChild(outerDiv, exisitingDiv);
      } else {
        wrapperElement.appendChild(outerDiv);
      }

      // check if hash_url is different than initially

      if(result.hash_id !== hash_id) {
        // redirected
        window.location.replace('/#/' + result.hash_id) ;
      } else {
        setActiveTo(hash_id.split('?')[0], true);
      }
    });
  } else {
    if(outer.hasAttribute('fresh')) {
      outer.removeAttribute('fresh');
    }
    // just switch to it
    setActiveTo(hash_id, true);
  }
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

document.addEventListener('DOMContentLoaded', function() {
  var hash = window.location.hash;
  if(hash === ""){
    hash = '#/index';
    window.location.hash = hash;
  }
  var loc = hash.split('/').slice(1)[0];
  // valid choices
  if(["index", "option"].indexOf(loc) < 0) {
    hash = '#/index';
    window.location.hash = hash;
    loc = "index";
  }
  setActiveTo(loc, false);
  wrapperElement.classList.remove('loading');
});

window.addEventListener('popstate', function(evt) {
  var hash = window.location.hash;
  var loc = hash.split('/').slice(1)[0];
  loadByHashId(loc);
});

//nextButton.onclick = function(evt) {
//  if(transitionInProgress) {
//    return;
//  }
//  var firstElement = wrapperElement.querySelector('.active');
//  var secondElement = firstElement.nextElementSibling || wrapperElement.firstElementChild;
//  var transitionType = getTransitionType();
//  transition(firstElement, secondElement, transitionType).then(function() {
//  });
//
//};
//
//previousButton.onclick = function(evt) {
//  if(transitionInProgress) {
//    return;
//  }
//  var firstElement = wrapperElement.querySelector('.active');
//  var secondElement = firstElement.previousSibling || wrapperElement.lastElementChild;
//  var transitionType = getTransitionType(true);
//  transition(firstElement, secondElement, transitionType).then(function() {
//  });
//};
