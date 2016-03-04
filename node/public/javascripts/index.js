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

var transitionInProgress = false;
var transition = function(firstElement, secondElement) {
  transitionInProgress = true;

  secondElement.classList.add('ready');

  var f, s;
  return new Promise(function(resolve, reject) {
    return setTimeout(function() {
      f = firstElement.firstChild.getBoundingClientRect();
      s = secondElement.firstChild.getBoundingClientRect();
      secondElement.firstChild.style.transform = "scale(" + f.width / s.width + ", " + f.height / s.height + ")";
      return setTimeout(function() {
        secondElement.classList.remove('ready');
        secondElement.classList.add('transitioning');
        secondElement.classList.add('active');
      
        firstElement.classList.add('transitioning');
        firstElement.classList.remove('active');

        firstElement.firstChild.style.transform = "scale(" + s.width / f.width + ", " + s.height / f.height + ")";
        secondElement.firstChild.style.transform = "";

        return setTimeout(function() {
          firstElement.firstChild.style.transform = "";
          firstElement.classList.remove('transitioning');
          secondElement.classList.remove('transitioning');
          transitionInProgress = false;
          return resolve();
        }, 500);
      }, 10);
    }, 10);
  });
};

document.addEventListener('DOMContentLoaded', function() {
  nextButton.onclick = function(evt) {
    if(transitionInProgress) {
      return;
    }
    var firstElement = wrapperElement.firstElementChild;
    var secondElement = wrapperElement.children[1];
    transition(firstElement, secondElement).then(function() {
      wrapperElement.appendChild(firstElement);
    });
  };
  previousButton.onclick = function(evt) {
    if(transitionInProgress) {
      return;
    }
    var firstElement = wrapperElement.firstElementChild;
    var secondElement = wrapperElement.lastElementChild;
    transition(firstElement, secondElement).then(function() {
      wrapperElement.insertBefore(secondElement, firstElement);
    });
  };
});
