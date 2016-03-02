var stage = document.getElementById('stage');

var httpRequest = function(url, method, data) {
  return new Promise(function(resolve, reject) {
    var r = new XMLHttpRequest();
    r.open(method, url, true);
    r.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
    r.setRequestHeader('Accept', 'application/json');
    r.onload = function() {
      return resolve(r);
    };
    var rejectFunc = function() {
      alert("there was an error making that request");
      return reject(r);
    };
    r.onabort = rejectFunc;
    r.onerror = rejectFunc;
    r.send(data ? JSON.stringify(data) : null);
  });
};

var createElementWithProp = function(elementName, properties) {
  var elem = document.createElement(elementName);
  for(var prop in properties) {
    elem.setAttribute(prop, properties[prop]);
  }
  return elem;
};

var renderResponse = function(responseData) {
  switch (responseData.type) {
    case "text":
      var div = createElementWithProp('div', {'class' : 'stage-element'});
      var childDiv = createElementWithProp('div');
      childDiv.textContent = responseData.value;
      div.appendChild(childDiv);
      stage.appendChild(div);
      var firDim = stage.firstChild.getBoundingClientRect();
      var secDim = stage.children[1].getBoundingClientRect();
      stage.classList.add('transitioning');
      setTimeout(function() {
        stage.firstChild.classList.add('removed');
        stage.style.transform = "scaleX(" + secDim.width / firDim.width + ") scaleY(" + secDim.height / firDim.height + ")";
        setTimeout(function() {
          stage.style.transform = "";
          stage.removeChild(stage.firstChild);
          setTimeout(function() {
            stage.classList.remove('transitioning');
          }, 1000);
        }, 500);
      }, 20000);

      break;

    default:
      alert("unsupported type, you screwed up");
  }

};

document.addEventListener('DOMContentLoaded', function(evt) {
  document.removeEventListener('DOMContentLoaded', this);
  setTimeout(function() {
    httpRequest('/', 'POST', {'hash' : window.location.hash}).then(function(result) {
      try {
        var res = JSON.parse(result.responseText);
        return renderResponse(res);
      } catch (err) {
        alert("there was an error with the response of that request");
      }
    }).catch(function(error) {
      console.log(error);
    });
  }, 1000);
});
