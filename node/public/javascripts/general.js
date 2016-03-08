var general = {
  // create dom element with properties
  createElementWithProp : function(elementName, properties) {
    var elem = document.createElement(elementName);
    for(var prop in properties) {
      elem.setAttribute(prop, properties[prop]);
    }
    return elem;
  },

  // remove children from dom element
  removeChildren : function(element) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  },

  // promisify xmlhttprequest
  makeRequest : function(url, method, data, updateFunc, alternativeEncoding) {
    return new Promise(function(resolve, reject) {
      var request = new XMLHttpRequest();
      request.open(method, url, true);
      if(alternativeEncoding === null) {
        // do nothing
      } else if (alternativeEncoding) {
        request.setRequestHeader("Content-Type", alternativeEncoding);
      } else {
        request.setRequestHeader("Content-Type", "application/json");
      }
      request.onload = function() {
        if (request.status >= 200 && request.status < 400) {
          return resolve(request);
        } else {
          return reject(request);
        }
      };
      request.onerror = function(error) {
        return reject(request);
      };
      if(updateFunc) {
        request.onprogress = updateFunc;
      }
      request.send(data);
    });
  }
};
