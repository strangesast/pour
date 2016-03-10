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
  },
  // from http://stackoverflow.com/a/5100158
  dataURItoBlob : function(dataURI) {
    // convert base64/URLEncoded data component to raw binary data held in a string
    var byteString;
    if (dataURI.split(',')[0].indexOf('base64') >= 0) {
      byteString = atob(dataURI.split(',')[1]);
    } else {
      byteString = unescape(dataURI.split(',')[1]);
    }

    // separate out the mime component
    var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];

    // write the bytes of the string to a typed array
    var ia = new Uint8Array(byteString.length);
    for (var i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }

    return new Blob([ia], {type:mimeString});
  }
};
