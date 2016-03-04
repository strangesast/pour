var createElementWithProp = function(elementName, properties) {
  var elem = document.createElement(elementName);
  for(var prop in properties) {
    elem.setAttribute(prop, properties[prop]);
  }
  return elem;
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
var nextButton = document.getElementById('next');
var previousButton = document.getElementById('previous');
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
}

nextButton.onclick = function(evt) {
  if(transitionInProgress) {
    return;
  }
  var firstElement = wrapperElement.firstElementChild;
  var secondElement = wrapperElement.children[1];
  var transitionType = getTransitionType();
  transition(firstElement, secondElement, transitionType).then(function() {
    wrapperElement.appendChild(firstElement);
  });
};

previousButton.onclick = function(evt) {
  if(transitionInProgress) {
    return;
  }
  var firstElement = wrapperElement.firstElementChild;
  var secondElement = wrapperElement.lastElementChild;
  var transitionType = getTransitionType(true);
  transition(firstElement, secondElement, transitionType).then(function() {
    wrapperElement.insertBefore(secondElement, firstElement);
  });
};

var setActiveTo = function(loc, animate) {
  var selector = '[hash-url="' + loc + '"]';
  if(animate) {
    console.log(selector);
  }
  var div = document.querySelector('[hash-url="' + loc + '"]');
  var oldDiv = document.querySelector('.active');
  oldDiv.classList.remove('active');
  div.classList.add('active');
};

document.addEventListener('DOMContentLoaded', function() {
  var hash = window.location.hash;
  if(hash === "") {
    history.pushState(null, null, '#/one');
  }
  var loc = hash.split('/').slice(1)[0];
  if(["one", "two", "three", "four"].indexOf(loc) < 0) {
    history.pushState(null, null, '#/one');
    loc = "one"
  }
  setActiveTo(loc, false);
  wrapperElement.classList.remove('loading');
});

window.addEventListener('popstate', function(evt) {
  var hash = window.location.hash;
  var loc = hash.split('/').slice(1)[0];
  setActiveTo(loc, true);
})
