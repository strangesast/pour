var WebSocketServer = require('ws').Server;
var net = require('net');
var url = require('url');
var util = require('util'); // util.inspect
var Kegerator = require('./models/kegerator');

var kegConnections = {};

module.exports = function(server) {
  var wss = new WebSocketServer({
    server: server,
    path: '/sockets'
  });

  var activeKegerator = null;

  wss.on('connection', connectionListener);
};

var probeKegerator = function(address, port) {
  return new Promise(function(resolve, reject) {
    var client = net.createConnection({
      port: port,
      host: address
    }, function() {
      client.write('temps');
    });
    client.on('error', function(err) {
      return reject(err);
    });
    client.on('data', function(data) {
      var encoded = data.toString();
      return setTimeout(function() {
        client.end()
        return resolve();
      }, 2000);
    });
  });
}

var activateKeg = function(obj) {
  Kegerator.findById(obj.id).then(function(kegerator) {
    var response = {kegerator: kegerator};
    if(kegerator) {
      return probeKegerator(kegerator.address, kegerator.port).then(function(result) {
        // probe succeeded
        response.message = 'probe succeeded';
        response.status = 'ok'
        return response;
      }).catch(function(err) {
        // probe failed
        response.message = 'probe failed with code: "' + err.code + '"';
        response.status = 'fail'
        return response;
      });
    } else {
      // not found
      response.message = 'keg with id not found';
      response.status = 'fail';
      return Promise.resolve(response);
    }
  });
};

var determineAction = function(actionName, data) {
  switch (actionName) {
    case "activate_keg":
      return activateKeg(data);
      break;
    default: 
      return Promise.resolve({
        message: "unknown action"
      });
  }
};

var parseMessage = function(message, jsonOnly) {
  var parsedMessage;
  try {
    parsedMessage = JSON.parse(message);
  } catch (e) {
    parsedMessage = jsonOnly ? null : message;
  }
  if(parsedMessage === null) {
    return Promise.reject({
      message: "invalid json"
    });
  } else {
    return Promise.resolve(parsedMessage);
  }
};

var messageListener = function(ws) {
  return function(message) {
    return parseMessage(message, true).then(function(result) {
      if('action' in result) {
        determineAction(result.action, result.data).then(function(action_result) {
          console.log('HERE!');
          ws.send(JSON.stringify(action_result));
        });
      } else {
        console.log('unknown');
        console.log(result);
      }
    });
  };
};

var connectionListener = function(ws) {
  ws.on('message', messageListener(ws));
}

var connectionListener1 = function(ws) {
  var loc = url.parse(ws.upgradeReq.url, true);

  ws.on('message', function(message) {
    var parsed;
    ws.send(JSON.stringify({
      type: 'message',
      message: 'received: ' + message
    }));

    try {
      parsed = JSON.parse(message);
    } catch (e) {
      return;
    }

    if(!parsed) {
      return;
    }

    if(parsed.currentHash && parsed.currentHash === "pouring") {
      if(activeKegerator !== null) {
        ws.send(JSON.stringify({
          type: "message",
          message: "begin pouring..."
        }));
      } else {
        ws.send(JSON.stringify({
          type: "message",
          message: "you must first set up kegerator"
        }));
      }
    } else if (parsed.activeKeg) {
      Kegerator.findById(parsed.activeKeg).then(function(result) {
        if(result) {
          activeKegerator = new net.Socket();
          activeKegerator.connect(result.port, result.address, function(err) {
            if(err) {
              return console.log(err);
            }
            ws.send(JSON.stringify({
              activeKeg: result.toJSON()
            }));
          });
          activeKegerator.on('error', function(err) {
            ws.send(JSON.stringify({
              type: 'message',
              message: 'failed to connect to "' + result.name + '"'
            }));
            activeKegerator = null;
          });
        } else {
          ws.send(JSON.stringify({
            type: "message",
            message: "kegerator not found"
          }));
        }

      }).catch(function(error) {
        ws.send(JSON.stringify({
          type: 'message',
          message: 'failed: ' + util.inspect(error)
        }));
      });
    } else if (parsed.action && parsed.action == "pour") {
      if(activeKegerator !== null) {

      }
    } else if (parsed.action && parsed.action == "temps") {

      if(activeKegerator !== null) {
        activeKegerator.on('data', function(data) {
          ws.send(JSON.stringify({
            type: "temperature_update",
            data: data.toString('utf-8')
          }));
        });
        activeKegerator.write('temps\n');
      }
    }

  });

  ws.send('welcome!');
};
