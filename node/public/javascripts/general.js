var general = {
  // create dom element with properties
  createElementWithProp : function(elementName, properties) {
    var elem = document.createElement(elementName);
    for(var prop in properties) {
      elem.setAttribute(prop, properties[prop]);
    }
    return elem;
  },

  // promisify xmlhttprequest
  makeRequest : function(url, method, data, updateFunc) {
    var contentType = "application/json";
    if(data && data.constructor && data.constructor === FormData) {
      contentType = "application/x-www-form-urlencoded";
    }
    return new Promise(function(resolve, reject) {
      var request = new XMLHttpRequest();
      request.open(method, url, true);
      request.setRequestHeader("Content-Type", contentType);
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
